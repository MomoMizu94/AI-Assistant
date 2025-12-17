using System;
using System.Diagnostics;
using System.Text;
using System.Collections;
using UnityEngine;
using UnityEngine.Networking;

public class LLMServerBackend : MonoBehaviour
{
    [Header("Paths for llama-server & LLM model")]
    public string serverPath;
    public string modelPath;

    [Header("Server settings")]
    public int serverPort = 8080;
    public int threads = 16;
    public int ngl = 999;

    [Header("Health check")]
    public float healthPollIntervalSeconds = 1f;
    public float healthTimeoutSeconds = 60f;

    // Holds OS process & bool for tracking
    private Process _process;
    public bool IsRunning
    {
        get
        {
            if (_process == null)
            {
                return false;
            }
            return !_process.HasExited;
        }
    }


    public void StartServerButton()
    {
        // Check if server is already running; if not, start it
        if (IsRunning == true)
        {
            UnityEngine.Debug.Log("LLM server already running (process exists).");
            return;
        }

        StartServer();
        StartCoroutine(WaitForHealthThenLogReady());
    }


    public void StopServerButton()
    {
        StopServer();
    }


    private void StartServer()
    {
        // Check for invalid paths
        if (string.IsNullOrWhiteSpace(serverPath) || string.IsNullOrWhiteSpace(modelPath))
        {
            UnityEngine.Debug.LogError("Missing serverPath or modelPath.");
            return;
        }

        // Build the server command arguments & new varible
        string args = $"-m \"{modelPath}\" -t {threads} -ngl {ngl} --port {serverPort}";
        var psi = new ProcessStartInfo
        {
            FileName = serverPath,
            Arguments = args,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true
        };

        // Create a process object with previous arguments/variable
        try
        {
            _process = new Process { StartInfo = psi, EnableRaisingEvents = true };

            // Hooks the output from the server to Debug.Log for debugging
            _process.OutputDataReceived += (_, e) => { if (!string.IsNullOrEmpty(e.Data)) UnityEngine.Debug.Log($"[llama-server] {e.Data}"); };
            _process.ErrorDataReceived  += (_, e) => { if (!string.IsNullOrEmpty(e.Data)) UnityEngine.Debug.LogWarning($"[llama-server] {e.Data}"); };
            _process.Exited += (_, __) => UnityEngine.Debug.LogWarning("LLM server process exited.");

            // Functions from System.Diagnostics
            _process.Start();
            _process.BeginOutputReadLine();
            _process.BeginErrorReadLine();

            // For debugging
            UnityEngine.Debug.Log($"Started LLM server PID={_process.Id}");
        }

        // Error handling
        catch (Exception ex)
        {
            UnityEngine.Debug.LogError($"Failed to start server: {ex.Message}");
            _process = null;
        }
    }


    private IEnumerator WaitForHealthThenLogReady()
    {
        // Creates variables for time (not effected by pause) and server url
        float start = Time.realtimeSinceStartup;
        string serverUrl = $"http://127.0.0.1:{serverPort}/health";

        // Repeats until timeout
        while (Time.realtimeSinceStartup - start < healthTimeoutSeconds)
        {
            using (var req = UnityWebRequest.Get(serverUrl))
            {
                // Timeout variable for single HTTP attempts
                req.timeout = 2; // seconds
                yield return req.SendWebRequest();

                // If successful response -> stop
                if (req.result == UnityWebRequest.Result.Success)
                {
                    UnityEngine.Debug.Log("LLM server is READY (health endpoint OK).");
                    yield break;
                }
            }
            
            // If not successful -> Wait a bit and retry
            yield return new WaitForSecondsRealtime(healthPollIntervalSeconds);
        }

        UnityEngine.Debug.LogError("LLM server did not become healthy within timeout.");
    }


    private void StopServer()
    {
        // Check whether server is running or not
        if (IsRunning == false)
        {
            UnityEngine.Debug.Log("No running LLM server process to stop.");
            return;
        }

        try
        {
            // If running, try to kill the server process
            _process.Kill();
            _process.Dispose();
            _process = null;

            UnityEngine.Debug.Log("LLM server stopped.");
        }

        // Error handling
        catch (Exception ex)
        {
            UnityEngine.Debug.LogError($"Failed to stop server: {ex.Message}");
        }
    }


    private void OnApplicationQuit()
    {
        // Stop the server when Unity quits, optional
        StopServer();
    }
}

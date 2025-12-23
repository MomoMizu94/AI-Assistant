using System;
using System.Collections;
using System.Collections.Generic;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;
using TMPro;

public class ConversationBackend : MonoBehaviour
{
    [Header("Server backend reference")]
    public LLMServerBackend serverBackend;

    [Header("LLM settings")]
    public string modelName = "Qwen3-32B-UD-Q6_K_XL.gguf";
    [Range(0f, 2f)] public float temperature = 0.7f;

    [Header("UI")]
    public TMP_InputField inputField;
    public Transform chatContent;
    public GameObject messagePrefab;

    private readonly List<ChatMessage> _messages = new List<ChatMessage>()
    {
        new ChatMessage { role = "system", content = "You are a concise and friendly AI assistant that gives answers without emojis." }
    };

    // Busy flag
    private bool _requestInFlight = false;
    

    public void OnSendButtonPressed()
    {
        // If request is running, ignore
        if (_requestInFlight == true)
        {
            return;
        }

        // Store inputField text in prompt
        string prompt = "";
        if (inputField != null)
        {
            prompt = inputField.text;
        }

        if (prompt == null)
        {
            prompt = "";
        }

        prompt = prompt.Trim();

        // If prompt is null or empty, return
        if (string.IsNullOrEmpty(prompt))
        {
            return;
        }

        // Append used messages to UI
        AppendMessage("user", prompt);
        AddMessageToUI("user", prompt);

        // Clear input field and bring back cursor
        inputField.text = "";
        inputField.ActivateInputField();

        StartCoroutine(SendMessageCoroutine(prompt));
    }


    private IEnumerator SendMessageCoroutine(string prompt)
    {
        // Reserve busy flag
        _requestInFlight = true;

        // Reference checks. Pause until server is ready
        if (serverBackend == null)
        {
            Debug.Log("ConversationBackend: The server reference is not set!");
            _requestInFlight = false;
            yield break;
        }
        yield return serverBackend.EnsureServerIsReady();

        // Safety checks
        if (serverBackend.IsRunning == false)
        {
            AddMessageToUI("system", "Server is not running!");
            _requestInFlight = false;
            yield break;
        }

        // Build the message json
        var messageBody = new ChatCompletionRequest{
            model = modelName,
            messages = _messages,
            temperature = temperature
        };
        string requestInJson = JsonUtility.ToJson(messageBody);

        string backendUrl = $"http://127.0.0.1:{serverBackend.serverPort}/v1/chat/completions";

        // Send request to LLMserver
        using (var payload = new UnityWebRequest(backendUrl, "POST"))
        {
            // Handle requests sent to server
            byte[] bodyRaw = Encoding.UTF8.GetBytes(requestInJson);
            payload.uploadHandler = new UploadHandlerRaw(bodyRaw);
            payload.downloadHandler = new DownloadHandlerBuffer();
            payload.SetRequestHeader("Content-Type", "application/json");
            payload.timeout = 120;

            yield return payload.SendWebRequest();

            // Handle responses from server
            if (payload.result != UnityWebRequest.Result.Success)
            {

                Debug.LogError("ConversationBackend: LLM request failed!");
                AddMessageToUI("system", "Error encountered while processing request.");
                _requestInFlight = false;
                yield break;
            }

            // Response from server in json
            string responseInJson = payload.downloadHandler.text;

            // Parse response
            ChatCompletionResponse parsedResponse;
            try
            {
                parsedResponse = JsonUtility.FromJson<ChatCompletionResponse>(responseInJson);
            }
            catch (Exception e)
            {
                Debug.LogError($"ConversationBackend: Failed to parse response JSON: {e.Message}\n{responseInJson}");
                AddMessageToUI("system", "Got a response but failed to parse it.");
                _requestInFlight = false;
                yield break;
            }

            // Extract the content of the response & clean it
            string responseContent = null;
            if (parsedResponse != null && parsedResponse.choices.Length > 0)
            {
                responseContent = parsedResponse.choices[0].message.content;
            }
            string cleanedResponseContent = CleanResponse(responseContent);

            // Add response to chat history
            AppendMessage("assistant", cleanedResponseContent);
            AddMessageToUI("assistant", cleanedResponseContent);
        }
        _requestInFlight = false;
    }


    private void AppendMessage(string role, string content)
    {
        _messages.Add(new ChatMessage
        {
            role = role,
            content = (content ?? "").Trim()
        });
    }


    private string CleanResponse(string text)
    {
        if (string.IsNullOrEmpty(text))
        {
            return "";
        }

        // Remove <think> blocks
        int endThink = text.IndexOf("</think>", StringComparison.OrdinalIgnoreCase);
        if (endThink >= 0)
        {
            text = text.Substring(endThink + "</think>".Length).Trim();
        }

        // Rest of the cleanup
        text = text.Replace("*", "").Replace("###", "").Replace("---", "").Trim();
        return text;
    }


    private void AddMessageToUI(string role, string text)
    {
        // Safety checks
        if (chatContent == null || messagePrefab == null)
        {
            Debug.LogWarning("Either chatContent or messagePrefab is missing!");
            return;
        }

        // Instantiate new chat bubble
        GameObject messageLoad = Instantiate(messagePrefab, chatContent);

        // Load component from prefab
        MessageUI uiForMessageLoad = messageLoad.GetComponent<MessageUI>();
        if (uiForMessageLoad == null)
        {
            uiForMessageLoad = messageLoad.GetComponentInChildren<MessageUI>();
        }

        if (uiForMessageLoad != null)
        {
            uiForMessageLoad.Setup(role, text);
        }
        else
        {
            Debug.LogWarning("Message prefab is missing MessageUI component!");
        }
    }



// ---------------- JSON MODELS ------------------
    [Serializable]
    // Payload sent to /v1/chat/completions
    public class ChatCompletionRequest
    {
        public string model;
        public List<ChatMessage> messages;
        public float temperature;
    }


    [Serializable]
    // Payload received from /v1/chat/completions
    public class ChatCompletionResponse
    {
        public Choice[] choices;
    }


    [Serializable]
    public class ChatMessage
    {
        public string role;
        public string content;
    }


    [Serializable]
    public class Choice
    {
        public Message message;
    }


    [Serializable]
    public class Message
    {
        public string role;
        public string content;
    }
}

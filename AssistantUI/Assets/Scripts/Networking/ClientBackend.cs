using UnityEngine;
using System.Net.Http;
using System.Threading.Tasks;


public class ClientBackend : MonoBehaviour
{
    private static HttpClient client = new HttpClient();
    public string serverUrl = "http://127.0.0.1:8080";

    public async Task<string> SendMessage(string text)
    {
        // Tool to help communicate with server
        var content = new StringContent(
            $"{{\"text\":\"{text}\"}}",
            System.Text.Encoding.UTF8,
            "application/json"
        );

        // For incoming traffic
        var response = await client.PostAsync(serverUrl + "/send", content);
        return await response.Content.ReadAsStringAsync();
    }
}
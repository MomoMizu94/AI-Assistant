using UnityEngine;
using UnityEngine.UI;
using TMPro;


public class ChatUI : MonoBehaviour
{
    public TMP_InputField chatBoxInputField;
    public ClientBackend backend;
    public Transform chatContainer;
    public GameObject messagePrefab;

    public async void OnSendButtonPressed()
    {
        string msg = chatBoxInputField.text;
        
    }
}

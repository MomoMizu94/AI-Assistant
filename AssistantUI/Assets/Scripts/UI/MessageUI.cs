using UnityEngine;
using TMPro;
using UnityEngine.UI;

public class MessageUI : MonoBehaviour
{
    public TMP_Text messageText;
    public Image chatBubble;

    public void Setup(string role, string text)
    {
        messageText.text = text;

        if (role == "user")
            chatBubble.color = Color.cyan;
        else
            chatBubble.color = Color.yellow;
    }
}

using UnityEngine;
using TMPro;
using UnityEngine.UI;

public class MessageUI : MonoBehaviour
{
    [Header("UI references")]
    [SerializeField] private TMP_Text messageText;
    [SerializeField] private Image chatBubble;

    [Header("Colors")]
    [SerializeField] private Color userColor = Color.cyan;
    [SerializeField] private Color assistantColor = Color.red;
    [SerializeField] private Color systemColor = Color.gray;

    public void Setup(string role, string text)
    {
        if (messageText != null)
        {
            messageText.text = text;
        }

        if (chatBubble == null)
        {
            return;
        }

        if (role == "user")
            chatBubble.color = userColor;
        else if (role == "assistant")
        {
            chatBubble.color = assistantColor;
        }
        else
        {
            chatBubble.color = systemColor;
        }
    }
}

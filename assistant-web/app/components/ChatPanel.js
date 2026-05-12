"use client";

import { useEffect, useRef } from "react";
import { Mic, MicOff } from "lucide-react";
import styles from "./ChatPanel.module.css";

export default function ChatPanel({
  messages,
  prompt,
  loading,
  activeChatId,
  health,
  audioState,
  onPromptChange,
  onSend,
  onClear,
  onToggleRecording,
}) {
  // Auto-scroll: a ref attached to an invisible div at the bottom of the message list.
  // useEffect watches the messages array — every time it changes, we scroll the div into view.
  const bottomRef = useRef(null);
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const serverRunning = health?.llm_server_running;

  return (
    <section className={styles.panel}>
      <div className={styles.messageList}>
        {messages.length === 0 && !loading && (
          <p className={styles.placeholder}>
            {activeChatId ? "Send a message to get started." : "Select or create a chat."}
          </p>
        )}

        {messages.map((m, i) => (
          <div key={i} className={styles.message}>
            <div className={`${styles.messageRole} ${m.role === "user" ? styles.messageRoleUser : ""}`}>
              {m.role}
            </div>
            <div className={styles.messageContent}>{m.content}</div>
          </div>
        ))}

        {loading && <div className={styles.thinking}>Thinking…</div>}

        {/* Invisible anchor for auto-scroll */}
        <div ref={bottomRef} />
      </div>

      <form className={styles.inputForm} onSubmit={onSend}>
        <input
          className={styles.textInput}
          value={prompt}
          onChange={(e) => onPromptChange(e.target.value)}
          placeholder="Type a message..."
          disabled={!activeChatId}
        />
        <button
          className={styles.sendBtn}
          disabled={loading || !activeChatId || (health && !serverRunning)}
        >
          Send
        </button>
        <button
          className={styles.iconBtn}
          type="button"
          onClick={onClear}
          disabled={loading || !activeChatId}
        >
          Clear
        </button>
        <button
          className={`${styles.iconBtn} ${audioState.recording ? styles.iconBtnActive : ""}`}
          type="button"
          onClick={onToggleRecording}
          disabled={loading || (health && !serverRunning)}
        >
          {audioState.recording ? <MicOff size={18} /> : <Mic size={18} />}
        </button>
      </form>
    </section>
  );
}

"use client";

import styles from "./StatusBar.module.css";

export default function StatusBar({
  health,
  chatsCount,
  audioState,
  loading,
  onStartServer,
  onStopServer,
  onToggleSpeakResponses,
}) {
  const serverRunning = health?.llm_server_running;

  return (
    <div className={styles.statusBar}>
      <div className={styles.group}>
        <span className={styles.label}>Backend</span>
        <span className={styles.value}>{health ? "Connected" : "..."}</span>
      </div>

      <div className={styles.group}>
        <span className={styles.label}>LLM Server</span>
        <span className={`${styles.value} ${health ? (serverRunning ? styles.valueRunning : styles.valueStopped) : ""}`}>
          {health ? (serverRunning ? "Running" : "Stopped") : "..."}
        </span>
      </div>

      {"busy" in (health || {}) && (
        <div className={styles.group}>
          <span className={styles.label}>Status</span>
          <span className={styles.value}>{health.busy ? "Busy" : "Idle"}</span>
        </div>
      )}

      {health && (
        <div className={styles.group}>
          <span className={styles.label}>Chats</span>
          <span className={styles.value}>{chatsCount}</span>
        </div>
      )}

      <div className={styles.controls}>
        <label className={styles.speakToggle}>
          <input
            className={styles.speakToggleInput}
            type="checkbox"
            checked={!!audioState.speak_responses}
            onChange={(e) => onToggleSpeakResponses(e.target.checked)}
          />
          <div className={styles.speakToggleTrack}>
            <div className={styles.speakToggleThumb} />
          </div>
          <span className={styles.speakToggleLabel}>Speak responses</span>
        </label>

        <div className={styles.buttons}>
          <button
            className={styles.btn}
            onClick={onStartServer}
            disabled={loading || (health && serverRunning)}
          >
            Start server
          </button>
          <button
            className={styles.btn}
            onClick={onStopServer}
            disabled={loading || (health && !serverRunning)}
          >
            Stop server
          </button>
        </div>
      </div>
    </div>
  );
}

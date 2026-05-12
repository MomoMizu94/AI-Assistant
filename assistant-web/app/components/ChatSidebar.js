"use client";

import { useRef } from "react";
import styles from "./ChatSidebar.module.css";

function formatChatTitle(chat) {
  return (chat?.title || "Chat").trim();
}

export default function ChatSidebar({
  chats,
  activeChatId,
  chatFilter,
  loading,
  onSelectChat,
  onFilterChange,
  onNewChat,
  onImport,
  onRename,
  onDelete,
  onExport,
}) {
  // fileInputRef lives here — it controls a DOM element that belongs to this component
  const fileInputRef = useRef(null);

  return (
    <aside className={styles.sidebar}>
      <div className={styles.topActions}>
        <button className={styles.btnPrimary} onClick={onNewChat} disabled={loading}>
          + New chat
        </button>
        <button
          className={styles.btnSecondary}
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={loading}
        >
          Import
        </button>

        {/* Hidden file input — triggered by the Import button above */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".json,application/json"
          style={{ display: "none" }}
          onChange={(e) => {
            const f = e.target.files?.[0];
            e.target.value = ""; // allow importing the same file twice
            if (f) onImport(f);
          }}
        />
      </div>

      <input
        className={styles.searchInput}
        value={chatFilter}
        onChange={(e) => onFilterChange(e.target.value)}
        placeholder="Search chats..."
      />

      {chats.map((c) => {
        const isActive = c.id === activeChatId;
        return (
          <div
            key={c.id}
            // Template literal lets us apply multiple classes conditionally
            className={`${styles.chatItem} ${isActive ? styles.chatItemActive : ""}`}
            onClick={() => onSelectChat(c.id)}
          >
            <div className={styles.chatTitle}>{formatChatTitle(c)}</div>
            <div className={styles.chatDate}>{c.updated_at}</div>

            {isActive && (
              <div className={styles.chatActions}>
                <button
                  className={styles.chatActionBtn}
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation(); // prevent re-selecting this chat
                    onRename(c.id);
                  }}
                >
                  Rename
                </button>
                <button
                  className={styles.chatActionBtn}
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(c.id);
                  }}
                >
                  Delete
                </button>
                <button
                  className={styles.chatActionBtn}
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onExport(c.id);
                  }}
                >
                  Export
                </button>
              </div>
            )}
          </div>
        );
      })}
    </aside>
  );
}

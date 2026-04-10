"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

export default function Home() {
  // Chat state
  const [chats, setChats] = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);

  // Current chat state
  const [messages, setMessages] = useState([]);
  const [prompt, setPrompt] = useState("");

  // UI state
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [health, setHealth] = useState(null);
  const [chatFilter, setChatFilter] = useState("");

  function formatChatTitle(chat) {
    return (chat?.title || "Chat").trim();
}

  // -------------- Backend Calls ----------------
  async function loadHealth() {
    const res = await fetch("/api/health");
    const data = await res.json();
    setHealth(data);
  }

  async function loadChats() {
    const res = await fetch("/api/chats");
    if (!res.ok)
      throw new Error("Failed to load chats!");
    const data = await res.json();
    setChats(data.chats ?? []);
    return data.chats ?? [];
  }

  async function loadSingleChat(chatId) {
    const res = await fetch(`/api/chats/${chatId}`);
    if (!res.ok)
      throw new Error("Failed to load the selected chat");
    const data = await res.json();
    setMessages(data.messages ?? []);
  }

  async function createNewChat() {
    setErr("");

    try {
      const res = await fetch("/api/chats", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ title: "New chat" }),
      });
      if (!res.ok)
        throw new Error("Failed to create a chat");
      const data = await res.json();
      const newChat = data.chat;

      const updatedList = await loadChats();
      setActiveChatId(newChat.id);
      await loadSingleChat(newChat.id);

      return updatedList;
    }
    catch (e) {
      setErr(e.message || "Failed to create new chat");
    }
  }

  async function clearActiveChat() {
    if (!activeChatId)
      return;
    setErr("");
    try {
      const res = await fetch(`/api/chats/${activeChatId}/clear`, { method: "POST" });
      if (!res.ok)
        throw new Error("Failed to clear chat");
      await loadSingleChat(activeChatId);
      await loadChats();
    } catch (e) {
      setErr(e.message || "Failed to clear chat.");
    }
  }

  async function startServer() {
    setErr("");
    try {
      await fetch("/api/server/start", { method: "POST" });
      await loadHealth();
    } catch {
      setErr("Failed to start the LLM server.");
    }
  }

  async function stopServer() {
    setErr("");
    try {
      await fetch("/api/server/stop", { method: "POST" });
      await loadHealth();
    } catch {
      setErr("Failed to stop the LLM server.");
    }
  }

  async function renameChat(chatId) {
    const currentChat = chats.find((c) => c.id === chatId);
    const newTitle = window.prompt("Rename chat:", currentChat?.title || "New chat");
    
    // User cancels
    if (newTitle == null)
    {
      return;
    }

    const title = newTitle.trim();
    if (!title)
    {
      return;
    }

    setErr("");
    try {
      const response = await fetch(`/api/chats/${chatId}/rename`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || "Renaming failed!");
      }
      await loadChats();
    } catch (e) {
      setErr(e.message || "Renaming failed!");
    }
  }

  async function deleteChat(chatId) {
    const currentChat = chats.find((c) => c.id === chatId);
    const ok = window.confirm(`Delete chat "${currentChat?.title || chatId}"? This can't be undone.`);
    if (!ok)
    {
      return;
    }

    setErr("");
    try {
      const response = await fetch(`/api/chats/${chatId}`, { method: "DELETE" });

      if (!response.ok)
      {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || "Deleting chat failed!");
      }

      const list = await loadChats();

      // Select new chat if active chat was deleted
      if (activeChatId == chatId) {
        if (list.length > 0)
        {
          setActiveChatId(list[0].id);
          await loadSingleChat(list[0].id);
        }
        else
        {
          await createNewChat();
        }
      }
    } catch (e) {
      setErr(e.message || "Deleting chat failed!");
    }
  }

  // ------------------ Boot ----------------------
  useEffect(() => {
    // Step 1: Load health
    loadHealth().catch(() => setErr("Failed to load server health. Make sure backend is running."));

    // Step 2: Load chats and pick default
    (async () => {
      try {
        const list = await loadChats();

        // If chats, pick most recently updated
        if (list.length > 0) {
          setActiveChatId(list[0].id);
          await loadSingleChat(list[0].id);
        } else {
          // If none exists, create new
          await createNewChat();
        }
      } catch {
        setErr("Failed to load chats!");
      }
    })();

    // Step 3: Poll health
    const id = setInterval(() => {
      loadHealth().catch(() => {});
    }, 3000);

    return () => clearInterval(id);
  }, []);

  // ---------------- Send function ---------------
  async function send(e) {
    e.preventDefault();
    const text = prompt.trim();
    if (!text || loading)
    {
      return; 
    }

    if (!activeChatId)
    {
      setErr("No chat selected. Create or select a chat first!");
      return;
    }

    if (health && !health.llm_server_running) {
      setErr("LLM server is stopped. Click 'Start server' first.");
      return;
    }

    setErr("");
    setLoading(true);

    // Show user message immediately
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setPrompt("");

    try {
      const res = await fetch(`/api/chats/${activeChatId}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: text }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Request failed (${res.status})`);
      }

      const data = await res.json();
      setMessages((prev) => [...prev, { role: "assistant", content: data.response }]);
      // Refresh sidebar timestamps after a message
      await loadChats();

    } catch (e) {
      setErr(e.message || "Failed to send.");
    } finally {
      setLoading(false);
    }
  }
  const filteredChats = chats.filter((c) => {
    const query = chatFilter.trim().toLowerCase();
    if (!query)
    {
      return true;
    }
    const title = (c.title || "").toLowerCase();
    return title.includes(query);
  });

  return (
    <main style={{ maxWidth: 1100, margin: "0 auto", padding: 16, fontFamily: "sans-serif" }}>
      
      <div style={{ display: "flex", alignItems: "center" }}>
        <h1 style={{ margin: 0 }}>AI Assistant</h1>
        <Link href="/settings" style={{ marginLeft: "auto" }}>Settings</Link>
      </div>

      {/* Top status bar */}
      <div
        style={{
          display: "flex",
          gap: 12,
          alignItems: "center",
          marginBottom: 12,
          padding: 10,
          border: "4px solid #474747",
          borderRadius: 8,
        }}
      >
        <div>
          <strong>Backend:</strong> {health ? "Connected" : "..."}
        </div>
        <div>
          <strong>LLM server:</strong>{" "}
          {health ? (health.llm_server_running ? "Running" : "Stopped") : "..."}
        </div>
        {"busy" in (health || {}) && (
          <div>
            <strong>Status:</strong> {health.busy ? "Busy" : "Idle"}
          </div>
        )}
        {health && (
          <div>
            <strong>Chats:</strong> {chats.length}
          </div>
        )}

        <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
          <button onClick={startServer} disabled={loading || (health && health.llm_server_running)}>
            Start server
          </button>
          <button onClick={stopServer} disabled={loading || (health && !health.llm_server_running)}>
            Stop server
          </button>
        </div>
      </div>

      {err && <div style={{ color: "crimson", marginBottom: 12 }}>{err}</div>}
      
      { /* Sidebar & chat panels */ }
      <div style={{ 
        display: "flex",
        gap: 12
      }}>
        { /* Sidebar */ }
        <aside
          style={{
            width: 280,
            border: "4px solid #474747",
            borderRadius: 8,
            padding: 12,
            height: 620,
            overflowY: "auto"
          }}
        >
          <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
            <button onClick={createNewChat} disabled={loading} style={{ flex: 1 }}>
              + New chat
            </button>
          </div>

          <input
            value={chatFilter}
              onChange={(e) => setChatFilter(e.target.value)}
              placeholder="Search chats..."
              style={{ width: "100%", padding: 8, borderRadius: 8, border: "2px solid #474747", marginBottom: 10 }}
          />

          {filteredChats.map((c) => {
            const isActive = c.id === activeChatId;
            return (
              <div
                key={c.id}
                onClick={async () => {
                  setErr("");
                  setActiveChatId(c.id);
                  try {
                    await loadSingleChat(c.id);
                  } catch {
                    setErr("Failed to load selected chat.");
                  }
                }}
                style={{
                  width: "100%",
                  textAlign: "left",
                  padding: 10,
                  marginBottom: 8,
                  borderRadius: 8,
                  border: isActive ? "4px solid #00ffff" : "2px solid #474747",
                  background: isActive ? "#111" : "transparent",
                  color: "inherit",
                  cursor: "pointer",
                }}
              >
                <div style={{ fontWeight: 700, marginBottom: 4 }}>{formatChatTitle(c)}</div>
                <div style={{ fontSize: 12, opacity: 0.75 }}>{c.updated_at}</div>
                {isActive && (
                  <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation(); // prevent selecting chat again
                        renameChat(c.id);
                      }}
                      style={{ padding: "6px 10px" }}
                    >
                      Rename
                    </button>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteChat(c.id);
                      }}
                      style={{ padding: "6px 10px" }}
                    >
                      Delete
                    </button>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (!activeChatId) return;
                        window.location.href = `/api/chats/${activeChatId}/export`;
                      }}
                      style={{ padding: "6px 10px" }}
                    >
                      Export
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </aside>

        {/* Chat panel */}
        <section style={{ flex: 1 }}>
          <div
            style={{
              border: "4px solid #474747",
              borderRadius: 8,
              padding: 12,
              minHeight: 320,
              maxHeight: 520,
              overflowY: "auto",
              marginBottom: 12,
            }}
          >
            {messages.map((m, i) => (
              <div key={i} style={{ marginBottom: 12 }}>
                <div style={{ fontWeight: 700, textTransform: "capitalize" }}>{m.role}</div>
                <div style={{ whiteSpace: "pre-wrap" }}>{m.content}</div>
              </div>
            ))}
            {loading && (
              <div>
                <em>Thinking…</em>
              </div>
            )}
          </div>

          <form onSubmit={send} style={{ display: "flex", gap: 8 }}>
                <input
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Type a message..."
                  style={{ flex: 1, padding: 10, borderRadius: 8, border: "4px solid #00ffff" }}
                  disabled={!activeChatId}
                />
                <button
                  disabled={loading || !activeChatId || (health && !health.llm_server_running)}
                  style={{ border: "4px solid #00ffff", borderRadius: 8, padding: "10px 14px" }}
                >
                  Send
                </button>
                <button
                  type="button"
                  onClick={clearActiveChat}
                  disabled={loading || !activeChatId}
                  style={{ border: "4px solid #00ffff", borderRadius: 8, padding: "10px 14px" }}
                >
                  Clear
                </button>
              </form>
            </section>
          </div>
    </main>
  );
}
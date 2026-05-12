"use client";

import { useEffect, useState } from "react";
import styles from "./page.module.css";
import Header from "./components/Header";
import StatusBar from "./components/StatusBar";
import ChatSidebar from "./components/ChatSidebar";
import ChatPanel from "./components/ChatPanel";

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

  // Audio
  const [audioState, setAudioState] = useState({ recording: false, speak_responses: false });

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

  async function importChat(file) {
    setErr("");

    try {
      const form = new FormData();
      form.append("file", file);

      const response = await fetch("/api/chats/import", {
        method: "POST",
        body: form,
      });

      const data = await await response.json().catch(() => ({}));
      // Catch errors
      if (!response.ok)
        throw new Error(data.detail || "Importing failed!");

      // Refresh and switch to imported chat
      await loadChats();
      setActiveChatId(data.chat.id);
      await loadSingleChat(data.chat.id);
    } catch (e) {
      setErr(e.message || "Importing failed!")
    }
  }

  async function loadAudioState() {
    const response = await fetch("/api/audio/state");
    const data = await response.json();
    setAudioState(data);
  }

  async function toggleSpeakResponses(enabled) {
    setErr("");

    try {
      const response = await fetch("/api/audio/speak_enabled", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      });
      const data = await response.json();
      setAudioState((prev) => ({ ...prev, speak_responses: data.speak_responses }));
    } catch {
      setErr("Failed to toggle response reading!");
    }
  }

  async function toggleRecording() {
    if (!activeChatId) {
      setErr("No chat selected!");
      return;
    }

    setErr("");
    try {
      const response = await fetch(`/api/audio/record/toggle?chat_id=${activeChatId}`, {
        method: "POST",
      });

      //const data = await response.json().catch(() => ({}));
      const text = await response.text();
      let data = {};
      try { data = JSON.parse(text); } catch {}

      if (!response.ok) {
        throw new Error(data.detail || data.error || text || "Failed to toggle recording!");
      }

      setAudioState((prev) => ({ ...prev, recording: !!data.recording }));

      // If recordgin just stopped and got response, append
      if (!data.recording && data.transcript) {
        setMessages((prev) => [
          ...prev,
          { role: "user", content: data.transcript },
          { role: "assistant", content: data.response },
        ]);
        // Upddate chats
        await loadChats();
      }
    } catch (e) {
      setErr(e.message || "Recording failed due to unknown reason.");
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

    // Step 4: Load audio state
    loadAudioState().catch(() => {});

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
    <main className={styles.root}>
      <Header />

      <StatusBar
        health={health}
        chatsCount={chats.length}
        audioState={audioState}
        loading={loading}
        onStartServer={startServer}
        onStopServer={stopServer}
        onToggleSpeakResponses={toggleSpeakResponses}
      />

      {err && <div className={styles.errorBanner}>{err}</div>}

      <div className={styles.layout}>
        <ChatSidebar
          chats={filteredChats}
          activeChatId={activeChatId}
          chatFilter={chatFilter}
          loading={loading}
          onSelectChat={async (id) => {
            setErr("");
            setActiveChatId(id);
            try { await loadSingleChat(id); }
            catch { setErr("Failed to load selected chat."); }
          }}
          onFilterChange={setChatFilter}
          onNewChat={createNewChat}
          onImport={importChat}
          onRename={renameChat}
          onDelete={deleteChat}
          onExport={(id) => { window.location.href = `/api/chats/${id}/export`; }}
        />

        <ChatPanel
          messages={messages}
          prompt={prompt}
          loading={loading}
          activeChatId={activeChatId}
          health={health}
          audioState={audioState}
          onPromptChange={setPrompt}
          onSend={send}
          onClear={clearActiveChat}
          onToggleRecording={toggleRecording}
        />
      </div>
    </main>
  );
}
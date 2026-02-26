"use client";

import { useEffect, useState } from "react";

export default function Home() {
  const [messages, setMessages] = useState([]);
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  async function loadHistory() {
    const res = await fetch("/api/history");
    const data = await res.json();
    setMessages(data.messages ?? []);
  }

  useEffect(() => {
    loadHistory().catch(() => setErr("Failed to load history."));
  }, []);

  async function send(e) {
    e.preventDefault();
    const text = prompt.trim();
    if (!text || loading) return;

    setErr("");
    setLoading(true);

    // Show user message immediately
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setPrompt("");

    try {
      const res = await fetch("/api/chat", {
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
    } catch (e) {
      setErr(e.message || "Failed to send.");
    } finally {
      setLoading(false);
    }
  }

  async function clear() {
    setErr("");
    try {
      await fetch("/api/clear", { method: "POST" });
      await loadHistory();
    } catch {
      setErr("Failed to clear history.");
    }
  }

  return (
    <main style={{ maxWidth: 900, margin: "0 auto", padding: 16, fontFamily: "sans-serif" }}>
      <h1>AI Assistant</h1>

      {err && <div style={{ color: "crimson", marginBottom: 12 }}>{err}</div>}

      <div
        style={{
          border: "1px solid #ddd",
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
        {loading && <div><em>Thinking…</em></div>}
      </div>

      <form onSubmit={send} style={{ display: "flex", gap: 8 }}>
        <input
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Type a message..."
          style={{ flex: 1, padding: 10, borderRadius: 8, border: "1px solid #ddd" }}
        />
        <button disabled={loading} style={{ padding: "10px 14px" }}>
          Send
        </button>
        <button type="button" onClick={clear} disabled={loading} style={{ padding: "10px 14px" }}>
          Clear
        </button>
      </form>
    </main>
  );
}
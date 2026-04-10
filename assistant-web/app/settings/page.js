"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

export default function SettingsPage() {
  const [settings, setSettings] = useState(null);     // effective settings (merged)
  const [draft, setDraft] = useState(null);           // editable copy
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [restartRequired, setRestartRequired] = useState(false);

  async function load() {
    setErr("");
    const res = await fetch("/api/settings");
    if (!res.ok) throw new Error("Failed to load settings.");
    const data = await res.json();
    setSettings(data.settings ?? {});
    setDraft(structuredClone(data.settings ?? {}));
  }

  useEffect(() => {
    load().catch((e) => setErr(e.message || "Failed to load settings."));
  }, []);

  const keys = useMemo(() => {
    if (!draft) return [];
    // Sort keys for stable UI; keep it simple alphabetical
    return Object.keys(draft).sort((a, b) => a.localeCompare(b));
  }, [draft]);

  function setField(key, value) {
    setDraft((prev) => ({ ...prev, [key]: value }));
  }

  function coerceForSave(value, originalType) {
    // Keep the backend simple: send types that match defaults as much as possible.
    // We’ll coerce number-like strings to numbers.
    if (originalType === "number") {
      if (value === "" || value === null || value === undefined) return value;
      const n = Number(value);
      return Number.isNaN(n) ? value : n;
    }
    if (originalType === "boolean") return Boolean(value);
    return value;
  }

  async function save() {
    if (!draft) return;
    setSaving(true);
    setErr("");
    setMsg("");
    setRestartRequired(false);

    try {
      // Build payload: send all settings (fine for your backend; it filters/overrides)
      // We preserve types where possible.
      const payload = {};
      for (const key of Object.keys(draft)) {
        const v = draft[key];
        const t = typeof (settings?.[key]);
        payload[key] = coerceForSave(v, t);
      }

      const res = await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "Failed to save settings.");

      setSettings(data.settings ?? payload);
      setDraft(structuredClone(data.settings ?? payload));

      setRestartRequired(!!data.restart_required);
      setMsg(!!data.restart_required ? "Saved. Restart required for some changes." : "Saved.");
    } catch (e) {
      setErr(e.message || "Failed to save settings.");
    } finally {
      setSaving(false);
    }
  }

  function renderField(key) {
    const original = settings?.[key];
    const value = draft?.[key];

    const type = typeof original;

    // Boolean → checkbox
    if (type === "boolean") {
      return (
        <label style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <input
            type="checkbox"
            checked={!!value}
            onChange={(e) => setField(key, e.target.checked)}
          />
          <span>{key}</span>
        </label>
      );
    }

    // Numbers → number input
    if (type === "number") {
      return (
        <label style={{ display: "grid", gap: 6 }}>
          <span style={{ fontWeight: 700 }}>{key}</span>
          <input
            type="number"
            value={value ?? ""}
            onChange={(e) => setField(key, e.target.value)}
            style={{ padding: 8, borderRadius: 8, border: "2px solid #474747" }}
          />
        </label>
      );
    }

    // Default: treat as string
    return (
      <label style={{ display: "grid", gap: 6 }}>
        <span style={{ fontWeight: 700 }}>{key}</span>
        <input
          type="text"
          value={value ?? ""}
          onChange={(e) => setField(key, e.target.value)}
          style={{ padding: 8, borderRadius: 8, border: "2px solid #474747" }}
        />
      </label>
    );
  }

  return (
    <main style={{ maxWidth: 1000, margin: "0 auto", padding: 16, fontFamily: "sans-serif" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <h1 style={{ margin: 0 }}>Settings</h1>
        <Link href="/" style={{ marginLeft: "auto" }}>← Back to chat</Link>
      </div>

      {err && <div style={{ color: "crimson", marginTop: 12 }}>{err}</div>}
      {msg && <div style={{ color: "limegreen", marginTop: 12 }}>{msg}</div>}
      {restartRequired && (
        <div style={{ marginTop: 8, padding: 10, border: "2px solid #ffb000", borderRadius: 8 }}>
          Some changes require restarting the llama server to take effect.
        </div>
      )}

      {!draft && !err && <p style={{ marginTop: 16 }}>Loading…</p>}

      {draft && (
        <div style={{ marginTop: 16, display: "grid", gap: 12 }}>
          <div style={{ display: "flex", gap: 8 }}>
            <button onClick={save} disabled={saving} style={{ padding: "10px 14px" }}>
              {saving ? "Saving…" : "Save"}
            </button>
            <button
              onClick={() => {
                setDraft(structuredClone(settings ?? {}));
                setErr("");
                setMsg("Reset changes.");
                setRestartRequired(false);
              }}
              disabled={saving}
              style={{ padding: "10px 14px" }}
            >
              Reset
            </button>
            <button
              onClick={() => load().then(() => setMsg("Reloaded.")).catch((e) => setErr(e.message))}
              disabled={saving}
              style={{ padding: "10px 14px" }}
            >
              Reload
            </button>
          </div>

          <div style={{ border: "3px solid #474747", borderRadius: 8, padding: 16 }}>
            <div style={{ display: "grid", gap: 14 }}>
              {keys.map((key) => (
                <div key={key}>{renderField(key)}</div>
              ))}
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import styles from "./settings.module.css";

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
    return Object.keys(draft).sort((a, b) => a.localeCompare(b));
  }, [draft]);

  function setField(key, value) {
    setDraft((prev) => ({ ...prev, [key]: value }));
  }

  function coerceForSave(value, originalType) {
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

    if (type === "boolean") {
      return (
        <label className={styles.checkboxLabel}>
          <input
            type="checkbox"
            checked={!!value}
            onChange={(e) => setField(key, e.target.checked)}
          />
          <span>{key}</span>
        </label>
      );
    }

    if (type === "number") {
      return (
        <label className={styles.fieldBlock}>
          <span className={styles.fieldName}>{key}</span>
          <input
            className={styles.input}
            type="number"
            value={value ?? ""}
            onChange={(e) => setField(key, e.target.value)}
          />
        </label>
      );
    }

    return (
      <label className={styles.fieldBlock}>
        <span className={styles.fieldName}>{key}</span>
        <input
          className={styles.input}
          type="text"
          value={value ?? ""}
          onChange={(e) => setField(key, e.target.value)}
        />
      </label>
    );
  }

  return (
    <main className={styles.root}>
      <div className={styles.header}>
        <h1 className={styles.title}>Settings</h1>
        <Link href="/" className={styles.backLink}>← Back to chat</Link>
      </div>

      {err && <div className={styles.errorBanner}>{err}</div>}
      {msg && <div className={styles.successBanner}>{msg}</div>}
      {restartRequired && (
        <div className={styles.warningBanner}>
          Some changes require restarting the LLM server to take effect.
        </div>
      )}

      {!draft && !err && <p className={styles.loading}>Loading…</p>}

      {draft && (
        <>
          <div className={styles.actions}>
            <button className={styles.btnPrimary} onClick={save} disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </button>
            <button
              className={styles.btn}
              onClick={() => {
                setDraft(structuredClone(settings ?? {}));
                setErr("");
                setMsg("Reset changes.");
                setRestartRequired(false);
              }}
              disabled={saving}
            >
              Reset
            </button>
            <button
              className={styles.btn}
              onClick={() => load().then(() => setMsg("Reloaded.")).catch((e) => setErr(e.message))}
              disabled={saving}
            >
              Reload
            </button>
          </div>

          <div className={styles.formCard}>
            <div className={styles.fieldGrid}>
              {keys.map((key) => (
                <div key={key}>{renderField(key)}</div>
              ))}
            </div>
          </div>
        </>
      )}
    </main>
  );
}

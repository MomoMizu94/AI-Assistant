"use client";

import Link from "next/link";
import { Settings } from "lucide-react";
import styles from "./Header.module.css";

export default function Header() {
  return (
    <header className={styles.header}>
      <h1 className={styles.title}>AI Assistant</h1>
      {/* aria-label replaces the missing visible text for screen readers */}
      <Link href="/settings" className={styles.settingsLink} aria-label="Settings">
        <Settings size={18} />
      </Link>
    </header>
  );
}

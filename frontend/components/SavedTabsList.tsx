"use client";
// Saved tabs: open / rename / delete (Phase 8). Rows are RLS-scoped to the user.
import { useCallback, useEffect, useState } from "react";
import { listTabs, renameTab, deleteTab, type SavedTab } from "../lib/supabase";
import type { TabDocument } from "../lib/tabFormat";

export default function SavedTabsList({ onOpen, refresh }:
  { onOpen: (id: string, title: string, doc: TabDocument) => void; refresh: number }) {
  const [tabs, setTabs] = useState<SavedTab[]>([]);
  const [err, setErr] = useState("");

  const load = useCallback(() => {
    listTabs().then(setTabs).catch((e) => setErr(String(e.message ?? e)));
  }, []);
  useEffect(load, [load, refresh]);

  if (err) return <p style={{ color: "#c62828" }}>saved tabs: {err}</p>;
  if (!tabs.length) return <p style={{ color: "#666" }}>no saved tabs yet</p>;
  return (
    <ul style={{ listStyle: "none", padding: 0 }}>
      {tabs.map((t) => (
        <li key={t.id} style={{ padding: "6px 0", borderBottom: "1px solid #eee" }}>
          <button style={{ ...link, fontWeight: 600 }}
                  onClick={() => onOpen(t.id, t.title, t.tab_json)}>{t.title}</button>
          <span style={{ color: "#999", fontSize: 12, marginLeft: 8 }}>
            {new Date(t.updated_at).toLocaleDateString()}
          </span>
          <button style={link} onClick={async () => {
            const name = prompt("rename tab", t.title);
            if (name) { await renameTab(t.id, name); load(); }
          }}>rename</button>
          <button style={{ ...link, color: "#c62828" }} onClick={async () => {
            if (confirm(`delete "${t.title}"?`)) { await deleteTab(t.id); load(); }
          }}>delete</button>
        </li>
      ))}
    </ul>
  );
}

const link: React.CSSProperties = {
  background: "none", border: 0, color: "#1565c0", cursor: "pointer",
  textDecoration: "underline", fontSize: 14, marginLeft: 8,
};

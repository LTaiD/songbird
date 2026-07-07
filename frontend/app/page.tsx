"use client";
// Songbird: record -> transcribe -> editable tab. Anonymous users get the full
// loop in-session; signing in adds save/open (Supabase, RLS).
import { useState } from "react";
import type { User } from "@supabase/supabase-js";
import Recorder from "../components/Recorder";
import TabEditor from "../components/TabEditor";
import AuthMenu from "../components/AuthMenu";
import SavedTabsList from "../components/SavedTabsList";
import { supabase, saveTab } from "../lib/supabase";
import type { TabDocument } from "../lib/tabFormat";

export default function Home() {
  const [doc, setDoc] = useState<TabDocument | null>(null);
  const [docId, setDocId] = useState<string | undefined>();
  const [title, setTitle] = useState("untitled tab");
  const [user, setUser] = useState<User | null>(null);
  const [refresh, setRefresh] = useState(0);
  const [saveMsg, setSaveMsg] = useState("");

  const save = async () => {
    if (!user || !doc) return;
    try {
      const id = await saveTab(user, title, doc, docId);
      setDocId(id);
      setRefresh((r) => r + 1);
      setSaveMsg("saved ✓");
      setTimeout(() => setSaveMsg(""), 2000);
    } catch (e) { setSaveMsg(String(e)); }
  };

  return (
    <main style={{ maxWidth: 960, margin: "0 auto", padding: 24 }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <h1 style={{ margin: 0 }}>🎸 Songbird</h1>
        <AuthMenu onUser={setUser} />
      </header>
      <p style={{ color: "#555" }}>Play into the camera; get an editable tab. No setup, no calibration.</p>

      {!doc && <Recorder onTab={(d) => { setDoc(d); setDocId(undefined); }} />}

      {doc && (
        <>
          <div style={{ display: "flex", gap: 8, alignItems: "center", margin: "12px 0" }}>
            <input value={title} onChange={(e) => setTitle(e.target.value)}
                   style={{ fontSize: 18, fontWeight: 600, border: 0, background: "none" }} />
            {user && <button onClick={save} style={btn}>save</button>}
            {!user && supabase && <span style={{ color: "#666", fontSize: 13 }}>sign in to save</span>}
            <span style={{ color: "#2e7d32" }}>{saveMsg}</span>
            <button onClick={() => { setDoc(null); setDocId(undefined); }}
                    style={{ ...btn, background: "#616161" }}>new recording</button>
          </div>
          <TabEditor doc={doc} onChange={setDoc} />
        </>
      )}

      {user && (
        <section style={{ marginTop: 32 }}>
          <h3>your tabs</h3>
          <SavedTabsList refresh={refresh}
            onOpen={(id, t, d) => { setDoc(d); setDocId(id); setTitle(t); }} />
        </section>
      )}
    </main>
  );
}

const btn: React.CSSProperties = {
  padding: "6px 14px", borderRadius: 6, border: 0, background: "#1565c0",
  color: "#fff", cursor: "pointer",
};

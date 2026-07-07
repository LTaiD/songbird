"use client";
// Email+password auth via Supabase (Phase 8). Hidden entirely when Supabase
// env isn't configured, so the app still runs record->edit locally.
import { useEffect, useState } from "react";
import type { User } from "@supabase/supabase-js";
import { supabase } from "../lib/supabase";

export default function AuthMenu({ onUser }: { onUser: (u: User | null) => void }) {
  const [user, setUser] = useState<User | null>(null);
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [msg, setMsg] = useState("");
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!supabase) return;
    supabase.auth.getUser().then(({ data }) => { setUser(data.user); onUser(data.user); });
    const { data: sub } = supabase.auth.onAuthStateChange((_e, session) => {
      setUser(session?.user ?? null);
      onUser(session?.user ?? null);
    });
    return () => sub.subscription.unsubscribe();
  }, [onUser]);

  if (!supabase) return null;

  const act = async (mode: "in" | "up") => {
    if (!supabase) return;
    setMsg("");
    const fn = mode === "in"
      ? supabase.auth.signInWithPassword({ email, password: pw })
      : supabase.auth.signUp({ email, password: pw });
    const { error } = await fn;
    setMsg(error ? error.message : mode === "up" ? "check your email to confirm" : "");
    if (!error) setOpen(false);
  };

  if (user) return (
    <span style={{ fontSize: 14 }}>
      {user.email}{" "}
      <button onClick={() => supabase!.auth.signOut()} style={link}>sign out</button>
    </span>
  );
  return (
    <span>
      <button onClick={() => setOpen(!open)} style={link}>sign in to save tabs</button>
      {open && (
        <span style={{ marginLeft: 8 }}>
          <input placeholder="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <input placeholder="password" type="password" value={pw}
                 onChange={(e) => setPw(e.target.value)} style={{ marginLeft: 4 }} />
          <button onClick={() => act("in")} style={link}>sign in</button>
          <button onClick={() => act("up")} style={link}>sign up</button>
          {msg && <em style={{ color: "#b26a00", marginLeft: 6 }}>{msg}</em>}
        </span>
      )}
    </span>
  );
}

const link: React.CSSProperties = {
  background: "none", border: 0, color: "#1565c0", cursor: "pointer",
  textDecoration: "underline", fontSize: 14,
};

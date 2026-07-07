"use client";
// SVG tab editor (spec §F): 6-line staff, chord stacks, low-confidence flags,
// select/edit/delete/add notes, duration/tuning/tempo/time-sig, playback.
import { useMemo, useRef, useState } from "react";
import type { Beat, Note, TabDocument } from "../lib/tabFormat";
import { LOW_CONFIDENCE } from "../lib/tabFormat";
import { playTab } from "../lib/audio";

const LINE = 18;          // px between string lines
const BEAT_W = 44;        // px per beat column
const PAD = 40;

interface Sel { m: number; b: number; n: number }

export default function TabEditor({ doc, onChange }:
  { doc: TabDocument; onChange: (d: TabDocument) => void }) {
  const [sel, setSel] = useState<Sel | null>(null);
  const playRef = useRef<AudioContext | null>(null);

  // beats laid out in a flat x sequence, measures separated by bar lines
  const cols = useMemo(() => {
    const out: { m: number; b: number; x: number; beat: Beat; bar: boolean }[] = [];
    let x = PAD;
    doc.measures.forEach((meas, mi) => {
      meas.beats.forEach((beat, bi) => {
        out.push({ m: mi, b: bi, x, beat, bar: false });
        x += BEAT_W * Math.max(beat.duration, 0.5);
      });
      out.push({ m: mi, b: -1, x, beat: { notes: [], duration: 0 }, bar: true });
      x += 12;
    });
    return { cols: out, width: x + PAD };
  }, [doc]);

  const mut = (fn: (d: TabDocument) => void) => {
    const copy: TabDocument = JSON.parse(JSON.stringify(doc));
    fn(copy);
    onChange(copy);
  };
  const selNote = (): Note | null =>
    sel ? doc.measures[sel.m]?.beats[sel.b]?.notes[sel.n] ?? null : null;

  // any user edit clears the low-confidence flag (spec §E)
  const editNote = (fn: (n: Note) => void) => sel && mut((d) => {
    const n = d.measures[sel.m].beats[sel.b].notes[sel.n];
    fn(n);
    n.confidence = 1.0;
  });

  const del = () => {
    if (!sel) return;
    mut((d) => { d.measures[sel.m].beats[sel.b].notes.splice(sel.n, 1); });
    setSel(null);
  };

  const addNote = (m: number, b: number, string: number) => mut((d) => {
    d.measures[m].beats[b].notes.push(
      { string, fret: 0, duration: d.measures[m].beats[b].duration, confidence: 1, articulations: [] });
  });

  const insertRest = () => sel && mut((d) => {
    d.measures[sel.m].beats.splice(sel.b + 1, 0, { notes: [], duration: 1 });
  });

  const play = () => {
    playRef.current?.close();
    playRef.current = playTab(doc);
  };

  const height = LINE * 5 + PAD * 2;
  const n = selNote();
  return (
    <div>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center", marginBottom: 8 }}>
        <button onClick={play} style={tbtn}>▶ play</button>
        <label>tempo <input type="number" value={doc.tempo} style={num}
          onChange={(e) => mut((d) => { d.tempo = +e.target.value; })} /></label>
        <label>time <input value={doc.timeSignature.join("/")} style={{ ...num, width: 48 }}
          onChange={(e) => {
            const [a, b] = e.target.value.split("/").map(Number);
            if (a && b) mut((d) => { d.timeSignature = [a, b]; });
          }} /></label>
        <label>tuning <input value={doc.tuning.join(" ")} style={{ ...num, width: 110 }}
          onChange={(e) => {
            const t = e.target.value.trim().split(/\s+/);
            if (t.length === 6) mut((d) => { d.tuning = t; });
          }} /></label>
        {n && (
          <span style={{ background: "#e3f2fd", padding: "4px 8px", borderRadius: 6 }}>
            fret <input type="number" value={n.fret} min={0} max={24} style={num}
              onChange={(e) => editNote((x) => { x.fret = +e.target.value; })} />
            string <input type="number" value={n.string} min={1} max={6} style={num}
              onChange={(e) => editNote((x) => { x.string = Math.min(6, Math.max(1, +e.target.value)); })} />
            beats <input type="number" value={n.duration} step={0.5} min={0.5} style={num}
              onChange={(e) => editNote((x) => { x.duration = +e.target.value; })} />
            <button onClick={del} style={{ ...tbtn, background: "#c62828" }}>delete</button>
            <button onClick={insertRest} style={tbtn}>+rest after</button>
          </span>
        )}
      </div>
      <svg width={cols.width} height={height} style={{ background: "#fffdf7", borderRadius: 8 }}>
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <line key={i} x1={PAD - 20} x2={cols.width - PAD + 20}
            y1={PAD + i * LINE} y2={PAD + i * LINE} stroke="#999" />
        ))}
        {doc.tuning.slice().reverse().map((t, i) => (
          <text key={i} x={8} y={PAD + i * LINE + 5} fontSize={12} fill="#666">{t}</text>
        ))}
        {cols.cols.map((c, ci) => c.bar ? (
          <line key={ci} x1={c.x} x2={c.x} y1={PAD} y2={PAD + 5 * LINE} stroke="#444" strokeWidth={2} />
        ) : (
          <g key={ci}>
            {/* click targets to add a note on any string of this beat */}
            {[1, 2, 3, 4, 5, 6].map((s) => (
              <rect key={s} x={c.x - 10} y={PAD + (s - 1) * LINE - 8} width={30} height={16}
                fill="transparent" style={{ cursor: "pointer" }}
                onClick={() => {
                  const idx = c.beat.notes.findIndex((nn) => nn.string === s);
                  idx >= 0 ? setSel({ m: c.m, b: c.b, n: idx }) : addNote(c.m, c.b, s);
                }} />
            ))}
            {c.beat.notes.map((nn, ni) => {
              const y = PAD + (nn.string - 1) * LINE;
              const isSel = sel && sel.m === c.m && sel.b === c.b && sel.n === ni;
              const flag = nn.confidence < LOW_CONFIDENCE;
              return (
                <g key={ni} style={{ cursor: "pointer" }}
                   onClick={() => setSel({ m: c.m, b: c.b, n: ni })}>
                  {(isSel || flag) && (
                    <circle cx={c.x} cy={y} r={10} fill={isSel ? "#bbdefb" : "#fff3e0"}
                      stroke={flag ? "#e65100" : "#1565c0"} strokeDasharray={flag ? "3 2" : ""} />
                  )}
                  <text x={c.x} y={y + 5} fontSize={14} textAnchor="middle"
                    fill={flag ? "#e65100" : "#111"} fontWeight={600}>{nn.fret}</text>
                </g>
              );
            })}
          </g>
        ))}
      </svg>
      <p style={{ color: "#666", fontSize: 13 }}>
        orange dashed = low-confidence read, click to review; editing clears the flag.
        click an empty line spot to add a note.
      </p>
    </div>
  );
}

const tbtn: React.CSSProperties = {
  padding: "6px 12px", borderRadius: 6, border: 0, background: "#1565c0",
  color: "#fff", cursor: "pointer",
};
const num: React.CSSProperties = { width: 56, margin: "0 6px" };

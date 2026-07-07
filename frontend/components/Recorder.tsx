"use client";
// Record flow (spec §3): framing preview + automatic pre-flight light ->
// count-in metronome -> record -> stop -> upload -> job progress -> tab JSON.
import { useEffect, useRef, useState } from "react";
import { WS_API, submitClip, pollJob, type JobStatus } from "../lib/api";
import { blobToWav, startMetronome } from "../lib/audio";
import type { TabDocument } from "../lib/tabFormat";

type Stage = "idle" | "preview" | "countin" | "recording" | "processing";

export default function Recorder({ onTab }: { onTab: (doc: TabDocument) => void }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const recRef = useRef<MediaRecorder | null>(null);
  const stopClickRef = useRef<(() => void) | null>(null);

  const [stage, setStage] = useState<Stage>("idle");
  const [ready, setReady] = useState(false);
  const [hints, setHints] = useState<string[]>([]);
  const [bpm, setBpm] = useState(90);
  const [useMetronome, setUseMetronome] = useState(true); // spec: default ON
  const [job, setJob] = useState<JobStatus | null>(null);
  const [error, setError] = useState("");

  useEffect(() => () => cleanup(), []);

  function cleanup() {
    wsRef.current?.close();
    stopClickRef.current?.();
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }

  async function openPreview() {
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 1280, height: 720 }, audio: true,
      });
      streamRef.current = stream;
      videoRef.current!.srcObject = stream;
      await videoRef.current!.play();
      setStage("preview");

      // preflight: send a JPEG every 700ms, render ready light + hints
      const ws = new WebSocket(`${WS_API}/preview`);
      wsRef.current = ws;
      const canvas = document.createElement("canvas");
      const send = () => {
        const v = videoRef.current;
        if (!v || ws.readyState !== 1) return;
        canvas.width = 640; canvas.height = 360;
        canvas.getContext("2d")!.drawImage(v, 0, 0, 640, 360);
        canvas.toBlob((b) => b && ws.send(b), "image/jpeg", 0.7);
      };
      ws.onopen = () => {
        const iv = setInterval(send, 700);
        const ka = setInterval(() => ws.readyState === 1 && ws.send("ping"), 15000);
        ws.onclose = () => { clearInterval(iv); clearInterval(ka); };
      };
      ws.onmessage = (e) => {
        const d = JSON.parse(e.data);
        if ("ready" in d) { setReady(d.ready); setHints(d.hints ?? []); }
      };
    } catch (e) {
      setError(`camera/mic unavailable: ${e}`);
    }
  }

  function beginRecording() {
    const stream = streamRef.current!;
    wsRef.current?.close(); // preview socket done; recording is batch
    const rec = new MediaRecorder(stream, { mimeType: "video/webm" });
    recRef.current = rec;
    const chunks: Blob[] = [];
    rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    rec.onstop = async () => {
      stopClickRef.current?.();
      setStage("processing");
      try {
        const webm = new Blob(chunks, { type: "video/webm" });
        const wav = await blobToWav(webm);
        const jobId = await submitClip(webm, wav, useMetronome ? bpm : undefined);
        const doc = await pollJob(jobId, setJob);
        cleanup();
        onTab(doc);
      } catch (e) {
        setError(String(e));
        setStage("preview");
      }
    };

    if (useMetronome) {
      setStage("countin");
      const ctx = new AudioContext();
      stopClickRef.current = startMetronome(ctx, bpm, 4, () => {
        rec.start();
        setStage("recording");
      });
      const prev = stopClickRef.current;
      stopClickRef.current = () => { prev(); ctx.close(); };
    } else {
      rec.start();
      setStage("recording");
    }
  }

  const light = ready ? "#2e7d32" : "#c62828";
  return (
    <div>
      {stage === "idle" && (
        <button onClick={openPreview} style={btn}>Record a take</button>
      )}
      <video ref={videoRef} muted playsInline
        style={{ width: "100%", maxWidth: 720, transform: "scaleX(-1)",
                 display: stage === "idle" || stage === "processing" ? "none" : "block",
                 borderRadius: 8 }} />
      {(stage === "preview") && (
        <div style={{ marginTop: 8 }}>
          <span style={{ color: light, fontWeight: 700 }}>
            ● {ready ? "ready — start when you like" : "adjusting…"}
          </span>
          {hints.map((h) => <div key={h} style={{ color: "#b26a00" }}>· {h}</div>)}
          <div style={{ margin: "8px 0" }}>
            <label>
              <input type="checkbox" checked={useMetronome}
                     onChange={(e) => setUseMetronome(e.target.checked)} /> metronome
            </label>
            {useMetronome && (
              <label style={{ marginLeft: 12 }}>
                bpm <input type="number" value={bpm} min={40} max={220}
                           onChange={(e) => setBpm(+e.target.value)} style={{ width: 60 }} />
              </label>
            )}
          </div>
          <button onClick={beginRecording} style={btn}>
            {useMetronome ? "Start (4-beat count-in)" : "Start recording"}
          </button>
        </div>
      )}
      {stage === "countin" && <p style={{ fontSize: 24 }}>count-in…</p>}
      {stage === "recording" && (
        <button onClick={() => recRef.current!.stop()} style={{ ...btn, background: "#c62828" }}>
          ■ Stop
        </button>
      )}
      {stage === "processing" && (
        <div>
          <p>transcribing… {job?.message ?? ""}</p>
          <progress value={job?.progress ?? 0} max={1} style={{ width: "100%" }} />
        </div>
      )}
      {error && <p style={{ color: "#c62828" }}>{error}</p>}
    </div>
  );
}

const btn: React.CSSProperties = {
  padding: "10px 18px", fontSize: 16, borderRadius: 6, border: 0,
  background: "#1565c0", color: "#fff", cursor: "pointer", marginTop: 8,
};

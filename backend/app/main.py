"""Songbird backend API (spec §3/§4): batch upload -> job -> result, plus the
live framing-preview WebSocket (the ONLY streaming — analysis is batch).

Stateless: no DB, no Supabase keys (frontend talks to Supabase directly),
recordings transient. CORS/WS origin restricted to the frontend.
"""
import os
import time

import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, Form, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from . import jobs
from .vision import preflight

FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")

app = FastAPI(title="Songbird")
app.add_middleware(CORSMiddleware, allow_origins=[FRONTEND_ORIGIN],
                   allow_methods=["*"], allow_headers=["*"])

# heavy CV singletons, created lazily so plain HTTP tests stay fast
_preview = {}


def _preview_deps():
    if not _preview:
        from .vision.hands import HandTracker
        from .vision.necksource import NeckSource
        _preview.update(hands=HandTracker(), neck=NeckSource(), t0=time.time())
    return _preview


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/transcribe")
async def submit(video: UploadFile = File(...), audio: UploadFile = File(...),
                 bpm: float | None = Form(None)):
    job_id = jobs.submit(await video.read(), await audio.read(), bpm=bpm)
    return {"job_id": job_id}


@app.get("/jobs/{job_id}")
def job_status(job_id: str):
    return jobs.status(job_id)


@app.websocket("/preview")
async def preview(ws: WebSocket):
    """Framing preview: client sends JPEG frames, server replies ready/hints.
    Keep-alive: any non-binary message is answered with a pong."""
    await ws.accept()
    deps = _preview_deps()
    try:
        while True:
            msg = await ws.receive()
            if msg.get("bytes"):
                arr = np.frombuffer(msg["bytes"], np.uint8)
                frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if frame is None:
                    await ws.send_json({"ready": False, "hints": ["bad frame"]})
                    continue
                ts = int((time.time() - deps["t0"]) * 1000)
                await ws.send_json(preflight.check(frame, deps["neck"], deps["hands"], ts))
            elif msg.get("text"):
                await ws.send_json({"pong": True})
            elif msg.get("type") == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        pass

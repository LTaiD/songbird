"""API E2E: upload synthesized clip -> poll job -> valid TabDocument back.
Run: .venv/bin/python -m backend.test_api
"""
import io
import time

import numpy as np
import cv2
import soundfile as sf
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.tab.schema import TabDocument
from backend.app.vision import markers_dev as md
from backend.app.audio.onsets import SR


def synth_clip():
    y = np.zeros(int(2 * SR), np.float32)
    for t in (0.5, 1.25):
        n = int(0.4 * SR); i = int(t * SR)
        y[i:i + n] += (np.sin(2 * np.pi * 110 * np.arange(n) / SR)
                       * np.exp(-np.arange(n) / (0.1 * SR))).astype(np.float32)
    buf = io.BytesIO(); sf.write(buf, y, SR, format="WAV")

    img = np.full((400, 600), 255, np.uint8); s = 80
    for mid, (cx, cy) in {0: (100, 100), 1: (500, 100), 2: (500, 300), 3: (100, 300)}.items():
        img[cy - s//2:cy + s//2, cx - s//2:cx + s//2] = \
            cv2.aruco.generateImageMarker(md._ARUCO_DICT, mid, s)
    frame = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    import tempfile, os
    mp4 = tempfile.mktemp(suffix=".mp4")
    vw = cv2.VideoWriter(mp4, cv2.VideoWriter_fourcc(*"mp4v"), 30, (600, 400))
    for _ in range(60):
        vw.write(frame)
    vw.release()
    vid = open(mp4, "rb").read(); os.unlink(mp4)
    return buf.getvalue(), vid


def main():
    wav, vid = synth_clip()
    c = TestClient(app)
    assert c.get("/health").json() == {"ok": True}

    r = c.post("/transcribe", files={"video": ("v.mp4", vid), "audio": ("a.wav", wav)},
               data={"bpm": 120})
    job_id = r.json()["job_id"]
    for _ in range(120):
        st = c.get(f"/jobs/{job_id}").json()
        if st["status"] != "running":
            break
        time.sleep(0.5)
    assert st["status"] == "done", st
    doc = TabDocument.model_validate(st["result"])
    notes = [n for m in doc.measures for b in m.beats for n in b.notes]
    assert len(notes) == 2 and all(n.confidence == 0.3 for n in notes), notes
    assert doc.tempo == 120
    print(f"API E2E OK: job {job_id[:8]} -> {len(notes)} notes, tempo {doc.tempo}")


if __name__ == "__main__":
    main()

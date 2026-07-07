"""Batch transcription pipeline (spec §D): audio+video files -> TabDocument.

    1 audio onsets (WHEN)          4 fuse (pitch cross-check, confidence)
    2 video sampled AT onsets      5 quantize to the (metronome) beat grid
    3 fretting reads (WHERE)       6 assemble -> Songbird tab JSON

Neck anchor source (vision/necksource.py): trained detector > ArUco rig >
classical lines+dots — so the full loop runs untrained on a bare guitar.
Raw audio/video are transient inputs; nothing is persisted here (spec §9).
"""
import cv2
import numpy as np

from ..audio import onsets, pitch, tempo
from ..vision.hands import HandTracker
from ..vision.contact import ContactHead
from ..vision.necksource import NeckSource
from ..vision import markers_dev as md
from .fuse import fuse
from .assemble import assemble

WINDOW = 0.12          # seconds either side of an onset to sample (spec §D.2)
FRAMES_PER_ONSET = 3   # temporal context beats a single mid-strike frame
MARKER_CONF = 0.8      # homography certainty for non-learned anchor paths


def _vision_reads(cap, fps, t, neck, hands, contact, ts_state):
    """Sample frames around onset t -> [(string, fret, confidence)]."""
    reads = []
    center = int(t * fps)
    for off in np.linspace(-WINDOW, WINDOW, FRAMES_PER_ONSET):
        idx = max(0, center + int(off * fps))
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok:
            continue
        read = neck.reader(frame)
        if read is None:
            continue
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        ts_state[0] += 33  # monotonic ms for MediaPipe VIDEO mode
        for landmarks, tips in hands.hands(rgb, ts_state[0], w, h):
            press = contact.press_prob(landmarks)
            for xy in tips:
                sf = read(xy)
                if sf:
                    reads.append((sf[0], sf[1], round(MARKER_CONF * press, 3)))
    return reads


def transcribe(video_path, audio_path, bpm=None, progress=lambda p, msg: None):
    """Full batch pass. progress(fraction, message) is called per stage."""
    progress(0.05, "loading audio")
    y = onsets.load(audio_path)
    progress(0.15, "detecting onsets")
    times = onsets.detect(y)
    grid_bpm, _ = tempo.beat_grid(known_bpm=bpm, y=y, sr=onsets.SR)

    hands, contact, neck = HandTracker(), ContactHead(), NeckSource()
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    ts_state = [0]
    vis, pitches = [], []
    for i, t in enumerate(times):
        progress(0.2 + 0.6 * (i + 1) / max(len(times), 1), f"reading onset {i + 1}/{len(times)}")
        vis.append(_vision_reads(cap, fps, t, neck, hands, contact, ts_state) if cap.isOpened() else [])
        m = pitch.pitch_at(y, onsets.SR, t)
        pitches.append(pitch.valid_positions(m) if m is not None else [])
    cap.release()

    progress(0.85, "fusing")
    events = fuse(list(times), vis, pitches)
    progress(0.95, "assembling tab")
    doc = assemble(events, bpm=grid_bpm)
    progress(1.0, "done")
    return doc


def _demo():
    """E2E on synthesized inputs: 2 A2 plucks + marker-only video (no hands) ->
    2 audio-only low-confidence notes at (5,0). Proves the whole batch path."""
    import tempfile, soundfile as sf
    sr = onsets.SR
    y = np.zeros(int(2 * sr), np.float32)
    for t in (0.5, 1.25):
        n = int(0.4 * sr)
        i = int(t * sr)
        y[i:i + n] += (np.sin(2 * np.pi * 110 * np.arange(n) / sr)
                       * np.exp(-np.arange(n) / (0.1 * sr))).astype(np.float32)
    wav = tempfile.mktemp(suffix=".wav"); sf.write(wav, y, sr)

    img = np.full((400, 600), 255, np.uint8); s = 80
    for mid, (cx, cy) in {0: (100, 100), 1: (500, 100), 2: (500, 300), 3: (100, 300)}.items():
        img[cy - s//2:cy + s//2, cx - s//2:cx + s//2] = \
            cv2.aruco.generateImageMarker(md._ARUCO_DICT, mid, s)
    frame = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    mp4 = tempfile.mktemp(suffix=".mp4")
    vw = cv2.VideoWriter(mp4, cv2.VideoWriter_fourcc(*"mp4v"), 30, (600, 400))
    for _ in range(60):
        vw.write(frame)
    vw.release()

    stages = []
    doc = transcribe(mp4, wav, bpm=120, progress=lambda p, m: stages.append(m))
    notes = [n for ms in doc.measures for b in ms.beats for n in b.notes]
    assert len(notes) == 2, notes
    assert all(n.string == 5 and n.fret == 0 and n.confidence == 0.3 for n in notes), notes
    assert doc.tempo == 120 and stages[-1] == "done"
    print(f"pipeline E2E OK: {len(notes)} audio-only notes at (5,0), "
          f"{len(doc.measures)} measure(s)")


if __name__ == "__main__":
    _demo()

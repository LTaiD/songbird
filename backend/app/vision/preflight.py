"""Pre-flight readiness check (spec §3) — an automatic ready/not-ready light,
NOT a calibration screen. Given one frame: neck anchored? hands visible?
lighting adequate? Returns ready + hints ("raise the camera"), never a task.
"""
import cv2
import numpy as np

MIN_BRIGHTNESS, MAX_BRIGHTNESS = 40, 220


def check(frame_bgr, neck_source, hand_tracker, ts_ms=0):
    hints = []
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    mean = float(np.mean(gray))
    if mean < MIN_BRIGHTNESS:
        hints.append("too dark — add light")
    elif mean > MAX_BRIGHTNESS:
        hints.append("too bright — reduce glare")

    if neck_source.reader(frame_bgr) is None:
        hints.append("fretboard not detected — angle the camera at the neck")

    h, w = frame_bgr.shape[:2]
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    n_hands = len(hand_tracker.hands(rgb, ts_ms, w, h))
    if n_hands == 0:
        hints.append("hands not visible — sit back so both hands are in frame")
    elif n_hands == 1:
        hints.append("only one hand visible")

    return {"ready": not hints, "hints": hints}


def _demo():
    class NoNeck:
        def reader(self, f): return None
    class Neck:
        def reader(self, f): return lambda xy: None
    class NoHands:
        def hands(self, *a): return []
    dark = np.zeros((100, 100, 3), np.uint8)
    r = check(dark, NoNeck(), NoHands())
    assert not r["ready"] and len(r["hints"]) == 3, r
    ok_frame = np.full((100, 100, 3), 128, np.uint8)
    class TwoHands:
        def hands(self, *a): return [1, 2]
    r = check(ok_frame, Neck(), TwoHands())
    assert r == {"ready": True, "hints": []}, r
    print("preflight self-check OK")


if __name__ == "__main__":
    _demo()

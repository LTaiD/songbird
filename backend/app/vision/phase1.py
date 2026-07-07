"""Phase 1 entrypoint: webcam -> markerless fretboard detector -> persistent neck
model (optical-flow locked) -> overlay (string, fret) on the fretting hand.

No markers, no calibration UI. Needs trained detector weights (see train_detector.py);
without them the neck won't lock and you'll see "searching".

Run (from repo root): python -m backend.app.vision.phase1
"""
import os
import time

import cv2

from .detector import Detector
from .tracking import NeckTracker
from .hands import HandTracker

WEIGHTS = "backend/app/models/fretboard_kps.weights.h5"
REDETECT_EVERY = 15  # run the heavy detector every N frames; optical-flow lock between


def main(cam=0, weights=WEIGHTS):
    if not os.path.exists(weights):
        print(f"WARNING: no weights at {weights} — train first (train_detector.py). "
              "Neck won't lock until then.")
    cap = cv2.VideoCapture(cam)
    if not cap.isOpened():
        raise SystemExit(f"cannot open camera {cam}")
    detector = Detector(weights=weights)
    neck = NeckTracker()
    hands = HandTracker()
    t0 = time.time()
    i = 0
    locked = False
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            h, w = frame.shape[:2]
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            if not locked or i % REDETECT_EVERY == 0:
                corr = detector.detect(frame)
                locked = bool(corr) and neck.set_detection(corr, gray)
            else:
                locked = neck.track(gray)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            disp = cv2.flip(frame, 1)
            for x, y in hands.fingertips(rgb, int((time.time() - t0) * 1000), w, h):
                xd = w - 1 - int(x)
                cv2.circle(disp, (xd, int(y)), 5, (0, 255, 255), -1)
                sf = neck.image_to_string_fret((x, y)) if locked else None
                if sf:
                    cv2.putText(disp, f"S{sf[0]} F{sf[1]}", (xd + 8, int(y) - 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            status = "neck: LOCKED" if locked else "neck: searching"
            cv2.putText(disp, status, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (0, 255, 0) if locked else (0, 0, 255), 2)
            cv2.imshow("Songbird Phase 1 (q to quit)", disp)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
            i += 1
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

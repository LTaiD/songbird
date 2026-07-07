"""Phase 0 entrypoint: webcam -> MediaPipe Hands -> ArUco homography -> overlay
(string, fret) on the fretting hand.

Run (from repo root): python -m backend.app.vision.phase0
Setup: python -m backend.app.vision.markers_dev --sheet  -> prints markers.png;
print it, cut the 4 markers, tape them at the fretboard corners per
markers_dev.py, aim the camera. Hold a chord -> labels appear.
"""
import time

import cv2

from . import markers_dev as md
from .hands import HandTracker


def main(cam=0):
    cap = cv2.VideoCapture(cam)
    if not cap.isOpened():
        raise SystemExit(f"cannot open camera {cam}")
    tracker = HandTracker()
    t0 = time.time()
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            h, w = frame.shape[:2]
            # Detect on the true frame — ArUco is chirality-sensitive, a mirrored
            # frame won't decode. Mirror only for display (drawn at xd = w-1-x).
            H = md.detect_homography(frame)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            ts = int((time.time() - t0) * 1000)
            disp = cv2.flip(frame, 1)

            for x, y in tracker.fingertips(rgb, ts, w, h):
                xd = w - 1 - int(x)
                cv2.circle(disp, (xd, int(y)), 5, (0, 255, 255), -1)
                if H is None:
                    continue
                sf = md.board_to_string_fret(*md.image_to_board(H, (x, y)))
                if sf:
                    cv2.putText(disp, f"S{sf[0]} F{sf[1]}", (xd + 8, int(y) - 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            status = "board: OK" if H is not None else "board: show 4 markers"
            cv2.putText(disp, status, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (0, 255, 0) if H is not None else (0, 0, 255), 2)
            cv2.imshow("Songbird Phase 0 (q to quit)", disp)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

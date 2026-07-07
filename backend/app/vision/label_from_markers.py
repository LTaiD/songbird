"""Auto-label training frames using the Phase-0 ArUco rig (replaces the deferred
synthetic generator as the label source).

Record clips with the 4 Phase-0 markers fixed at the neck corners (per
markers_dev.py). This tool detects the marker homography per frame and PROJECTS
the known neck positions of the nut and inlays into the image — free ground-truth
keypoints, no manual clicking. Train the markerless detector on these, then
remove the markers for inference.

Setup note: place markers just OUTSIDE the fret playing area so they don't
occlude the nut/inlays. Pass --inpaint to blank the marker quads in saved frames
so the detector can't cheat off them.

Run: python -m backend.app.vision.label_from_markers <clip.mp4> <out_dir> [--inpaint] [--every N]
Output: out_dir/<clip>_<frame>.png + .json ({nut:[lo,hi], inlays:{n:[x,y]}, dot12:[x,y]}).
"""
import os
import sys
import json

import numpy as np
import cv2

from . import markers_dev as md
from .fretboard import inlay_u

# markers_dev board-u is normalized to the 12th fret (u=1 @ fret 12); scale-length
# fraction (fretboard.inlay_u) is half that, so board_u = 2 * scale_fraction.
LABEL_FRETS = [3, 5, 7, 9, 12]  # within the nut..12th marker span (reliable)


def _project(Hinv, board_uv):
    p = cv2.perspectiveTransform(np.float32([[list(board_uv)]]), Hinv)[0, 0]
    return [float(p[0]), float(p[1])]


def label_frame(frame):
    """Return keypoint dict for one frame, or None if the 4 markers aren't seen."""
    H = md.detect_homography(frame)
    if H is None:
        return None
    Hinv = np.linalg.inv(H)
    nut = [_project(Hinv, (0.0, 0.0)), _project(Hinv, (0.0, 1.0))]
    inlays = {str(n): _project(Hinv, (2 * inlay_u(n), 0.5)) for n in LABEL_FRETS}
    return {"nut": nut, "inlays": inlays, "dot12": inlays["12"]}


def _inpaint_markers(frame):
    corners, ids, _ = md._DETECTOR.detectMarkers(frame)
    if ids is None:
        return frame
    mask = np.zeros(frame.shape[:2], np.uint8)
    for c in corners:
        cv2.fillConvexPoly(mask, c.reshape(4, 2).astype(np.int32), 255)
    return cv2.inpaint(frame, cv2.dilate(mask, np.ones((9, 9), np.uint8)), 3, cv2.INPAINT_TELEA)


def main(clip, out_dir, inpaint=False, every=5):
    os.makedirs(out_dir, exist_ok=True)
    cap = cv2.VideoCapture(clip)
    stem = os.path.splitext(os.path.basename(clip))[0]
    i = saved = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if i % every == 0:
            kp = label_frame(frame)
            if kp:
                img = _inpaint_markers(frame) if inpaint else frame
                base = os.path.join(out_dir, f"{stem}_{i:06d}")
                cv2.imwrite(base + ".png", img)
                json.dump(kp, open(base + ".json", "w"))
                saved += 1
        i += 1
    cap.release()
    print(f"labeled {saved} frames -> {out_dir}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 2:
        raise SystemExit(__doc__)
    every = int(a[a.index("--every") + 1]) if "--every" in a else 5
    main(a[0], a[1], inpaint="--inpaint" in a, every=every)

"""Unified neck-anchor source, in strict accuracy order:

  1. trained keypoint detector (detector.py)   — when weights exist
  2. ArUco dev rig (markers_dev.py)             — when markers are in frame
  3. classical lines + inlay dots (classical.py) — bare guitar, untrained

All three emit the same currency: (image_xy, (u, v)) correspondences for
fretboard.NeckModel, so pipeline/preflight/phase1 don't care which fired.
"""
import os

import numpy as np
import cv2

from .fretboard import NeckModel, fret_u
from .classical import ClassicalDetector
from . import markers_dev as md

DETECTOR_WEIGHTS = "backend/app/models/fretboard_kps.weights.h5"
# markers_dev board-u is normalized to fret 12 (u_board=1 there); neck-u is the
# scale-length fraction, so board (bu, bv) -> neck (bu * fret_u(12), bv).
_BOARD_CORNERS = [(0.0, 0.0), (0.0, 1.0), (1.0, 0.0), (1.0, 1.0)]


class NeckSource:
    def __init__(self, weights=DETECTOR_WEIGHTS):
        self.detector = None
        if os.path.exists(weights):
            from .detector import Detector
            self.detector = Detector(weights=weights)
        self.classical = ClassicalDetector()

    def correspondences(self, frame_bgr):
        if self.detector:
            corr = self.detector.detect(frame_bgr)
            if corr:
                return corr
        H = md.detect_homography(frame_bgr)
        if H is not None:
            Hinv = np.linalg.inv(H)
            corr = []
            for bu, bv in _BOARD_CORNERS:
                p = np.float32([[[bu, bv]]])
                x, y = cv2.perspectiveTransform(p, Hinv)[0, 0]
                corr.append(((float(x), float(y)), (bu * fret_u(12), bv)))
            return corr
        return self.classical.detect(frame_bgr)

    def reader(self, frame_bgr):
        """-> callable (x, y) -> (string, fret) | None, or None if no neck."""
        corr = self.correspondences(frame_bgr)
        if not corr:
            return None
        m = NeckModel()
        return m.image_to_string_fret if m.fit_points(corr) else None


def _demo():
    import cv2
    from .classical import _synthetic_neck
    src = NeckSource(weights="/nonexistent")
    assert src.detector is None

    # ArUco path: marker frame -> board center reads (3, 5) (see markers_dev)
    img = np.full((400, 600), 255, np.uint8); s = 80
    for mid, (cx, cy) in {0: (100, 100), 1: (500, 100), 2: (500, 300), 3: (100, 300)}.items():
        img[cy - s//2:cy + s//2, cx - s//2:cx + s//2] = \
            cv2.aruco.generateImageMarker(md._ARUCO_DICT, mid, s)
    read = src.reader(cv2.cvtColor(img, cv2.COLOR_GRAY2BGR))
    assert read and read((300, 200)) == (3, 5)

    # classical path: bare synthetic neck -> fret 7 read
    frame, pt, wx, y0, y1 = _synthetic_neck()
    read = src.reader(frame)
    assert read and read(pt(wx(7) - 4, y0 + 0.8 * (y1 - y0))) == (2, 7)

    # nothing in frame -> None
    assert src.reader(np.full((100, 100, 3), 128, np.uint8)) is None
    print("necksource self-check OK (aruco + classical fallbacks)")


if __name__ == "__main__":
    _demo()

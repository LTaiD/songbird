"""Optical-flow persistence for the neck model (Phase 1).

The detector is heavy, so run it every N frames; between runs, carry the neck
homography by tracking the anchor points (nut endpoints, inlays) with sparse
Lucas-Kanade optical flow and re-fitting. Their neck (u, v) coords are fixed, so
refitting from the moved image points keeps the model locked. When too many
points are lost (occlusion / big move), report loss so the caller re-detects.
"""
import numpy as np
import cv2

from .fretboard import NeckModel

MIN_POINTS = 4  # homography needs >=4 correspondences


class NeckTracker:
    def __init__(self, num_strings=6):
        self.model = NeckModel(num_strings)
        self.pts = None   # (N,2) image points under track
        self.neck = None  # (N,2) their fixed (u,v)
        self.prev_gray = None

    def set_detection(self, correspondences, gray=None):
        """Seed/refresh from detector output; returns True if a model was fit."""
        self.pts = np.float32([p for p, _ in correspondences])
        self.neck = np.float32([uv for _, uv in correspondences])
        if gray is not None:
            self.prev_gray = gray
        return self._refit()

    def track(self, gray):
        """Advance the lock to a new frame. False => lost, caller should re-detect.
        ponytail: lost points are dropped, not re-acquired, so the model degrades
        until the next detect() refreshes it — fine at a modest re-detect cadence."""
        if self.prev_gray is None or self.pts is None or len(self.pts) < MIN_POINTS:
            self.prev_gray = gray
            return False
        new, st, _ = cv2.calcOpticalFlowPyrLK(
            self.prev_gray, gray, self.pts.reshape(-1, 1, 2), None)
        keep = st.reshape(-1).astype(bool)
        if keep.sum() < MIN_POINTS:
            return False
        self.pts = new.reshape(-1, 2)[keep]
        self.neck = self.neck[keep]
        self.prev_gray = gray
        return self._refit()

    def image_to_string_fret(self, pt_xy):
        return self.model.image_to_string_fret(pt_xy)

    def _refit(self):
        corr = list(zip([tuple(p) for p in self.pts],
                        [tuple(uv) for uv in self.neck]))
        return self.model.fit_points(corr)


def _demo():
    import cv2 as _cv2
    from .fretboard import fret_u

    neck_quad = np.float32([(0, 0), (0.6, 0), (0.6, 1), (0, 1)])
    img_quad = np.float32([(100, 100), (500, 120), (480, 300), (120, 340)])
    Hgt = _cv2.getPerspectiveTransform(neck_quad, img_quad)

    def to_img(u, v):
        p = _cv2.perspectiveTransform(np.float32([[[u, v]]]), Hgt)[0, 0]
        return (float(p[0]), float(p[1]))

    corr = [(to_img(0, 0), (0, 0)), (to_img(0, 1), (0, 1)),
            (to_img(fret_u(5), 0.5), (fret_u(5), 0.5)),
            (to_img(fret_u(9), 0.5), (fret_u(9), 0.5))]
    tip = to_img(fret_u(7), 0.4)

    tr = NeckTracker()
    assert tr.set_detection(corr)
    assert tr.image_to_string_fret(tip) == (4, 7)
    # Rigid shift of all anchors + the fingertip preserves the (string, fret) read.
    dx, dy = 15, -8
    tr.set_detection([((p[0] + dx, p[1] + dy), uv) for p, uv in corr])
    assert tr.image_to_string_fret((tip[0] + dx, tip[1] + dy)) == (4, 7)

    # Optical flow: a textured frame shifted by a known vector -> LK recovers it.
    img = np.zeros((200, 200), np.uint8)
    squares = [(50, 50), (150, 60), (80, 150), (140, 140)]
    for x, y in squares:
        _cv2.rectangle(img, (x - 5, y - 5), (x + 5, y + 5), 255, -1)
    dx, dy = 6, 4
    img2 = _cv2.warpAffine(img, np.float32([[1, 0, dx], [0, 1, dy]]), (200, 200))
    tr2 = NeckTracker()
    tr2.set_detection([(squares[0], (0, 0)), (squares[1], (0, 1)),
                       (squares[2], (0.3, 0.5)), (squares[3], (0.5, 0.5))], gray=img)
    assert tr2.track(img2)
    moved = tr2.pts.mean(axis=0) - np.float32(squares).mean(axis=0)
    assert abs(moved[0] - dx) < 2 and abs(moved[1] - dy) < 2, moved
    print("tracking self-check OK (refit under motion + optical-flow lock)")


if __name__ == "__main__":
    _demo()

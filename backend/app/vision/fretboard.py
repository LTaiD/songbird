"""Markerless persistent neck model (Phase 1 core geometry).

Replaces the Phase-0 ArUco shortcut (markers_dev.py) with a homography anchored
on guitar-native features: the nut and identified fret lines. Feature *detection*
(classical CV or a trained detector) lives elsewhere and only has to hand this
model 2D correspondences — this file is the geometry, detector-agnostic.

Coordinate frame — neck (u, v):
  u = distance-from-nut as a fraction of scale length (0 = nut, 0.5 = 12th fret,
      -> 1 = bridge). Equal-tempered: fret n sits at u_n = 1 - 2^(-n/12).
  v = across strings, 0 = low-E (6th), 1 = high-E (1st).

Why this beats "count the frets": fret number is a *pure function of position*,
n(u) = -12*log2(1-u). Reveal a new fret on a posture shift and it gets the right
number automatically — nothing is ever counted, so nothing can double-count.
Scale length in cm is never needed; u is scale-invariant, so "self-calibrating
scale length" reduces to identifying *which* fret each detected line is (the
12th-fret double-dot disambiguates numbering). See fret_u / string_fret below.

Persistence across frames (optical-flow lock, re-detect-on-recover) is tracking.py.
"""
import math

import numpy as np
import cv2

NUM_STRINGS = 6


def fret_u(n):
    """Neck-u of fret n (equal temperament)."""
    return 1.0 - 2.0 ** (-n / 12.0)


def inlay_u(n):
    """Neck-u of the position-inlay dot for fret n — centered in the nth fret
    space, i.e. midway between fret wires n-1 and n."""
    return 0.5 * (fret_u(n - 1) + fret_u(n))


def string_fret(u, v, num_strings=NUM_STRINGS):
    """Neck (u, v) -> (string, fret), or None if off the playable neck."""
    eps = 1e-4  # tolerance: real reads (and float round-trips) land just off the nut
    if not (-eps <= u < 1.0 and -eps <= v <= 1.0 + eps):
        return None
    u = max(u, 0.0)
    fret = round(-12.0 * math.log2(1.0 - u))
    string = num_strings - round(v * (num_strings - 1))
    return int(string), int(fret)


class NeckModel:
    """Image<->neck homography built from a nut line + identified fret lines.

    Anchors are line *endpoints* on the low-E and high-E edges of the neck:
      nut:  ((x,y) low-E edge, (x,y) high-E edge)      -> u = 0
      fret: (n, (x,y) low-E edge, (x,y) high-E edge)   -> u = fret_u(n)
    Need the nut + >=1 fret (4 points) to solve; more frets => least-squares fit
    that averages out detection noise (the "scale-length fit").
    """

    def __init__(self, num_strings=NUM_STRINGS):
        self.num_strings = num_strings
        self.H = None  # image -> neck

    def fit(self, nut, frets):
        pts = []
        for (lo, hi), u in _lines_with_u(nut, frets):
            pts += [(lo, (u, 0.0)), (hi, (u, 1.0))]
        return self.fit_points(pts)

    def fit_points(self, correspondences):
        """Fit from arbitrary (image_xy, (u, v)) pairs — e.g. nut endpoints plus
        inlay dot centers at v=0.5. Needs >=4 (no 3 collinear)."""
        if len(correspondences) < 4:
            return False
        img_pts = np.float32([p for p, _ in correspondences])
        neck_pts = np.float32([uv for _, uv in correspondences])
        H, _ = cv2.findHomography(img_pts, neck_pts)
        self.H = H
        return H is not None

    def image_to_string_fret(self, pt_xy):
        if self.H is None:
            return None
        p = np.float32([[[pt_xy[0], pt_xy[1]]]])
        u, v = cv2.perspectiveTransform(p, self.H)[0, 0]
        return string_fret(float(u), float(v), self.num_strings)


def _lines_with_u(nut, frets):
    yield nut, 0.0
    for n, lo, hi in frets:
        yield (lo, hi), fret_u(n)


def _demo():
    # Ground-truth neck->image homography (a trapezoid = neck seen in perspective).
    neck_quad = np.float32([(0, 0), (0.6, 0), (0.6, 1), (0, 1)])
    img_quad = np.float32([(100, 100), (500, 120), (480, 300), (120, 340)])
    Hgt = cv2.getPerspectiveTransform(neck_quad, img_quad)

    def to_img(u, v):
        p = cv2.perspectiveTransform(np.float32([[[u, v]]]), Hgt)[0, 0]
        return (float(p[0]), float(p[1]))

    def fret_line(n):
        return (n, to_img(fret_u(n), 0.0), to_img(fret_u(n), 1.0))

    nut = (to_img(0, 0), to_img(0, 1))

    # Full fit (nut + frets 5 and 12) -> read a known point back.
    m = NeckModel()
    assert m.fit(nut, [fret_line(5), fret_line(12)])
    # string 4 is v=0.4 (6 - round(0.4*5) = 4); check fret 7
    assert m.image_to_string_fret(to_img(fret_u(7), 0.4)) == (4, 7)
    assert m.image_to_string_fret(to_img(fret_u(0), 1.0)) == (1, 0)  # nut, high E

    # No-double-count / reveal-a-new-fret: fit with ONLY nut + fret 5, then query
    # fret 9 (never given). Positional numbering still returns 9, not a miscount.
    m2 = NeckModel()
    assert m2.fit(nut, [fret_line(5)])
    assert m2.image_to_string_fret(to_img(fret_u(9), 0.0)) == (6, 9)
    assert m2.image_to_string_fret(to_img(fret_u(3), 0.0)) == (6, 3)

    # Behind the nut -> off the neck.
    assert m.image_to_string_fret(to_img(-0.05, 0.5)) is None
    print("fretboard self-check OK (markerless homography + positional numbering)")


if __name__ == "__main__":
    _demo()

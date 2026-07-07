"""Markerless fretboard keypoint detector (Phase 1).

Small custom Keras(torch) heatmap model on a permissively-licensed
`keras.applications` backbone — our own weights, no third-party model license
(unlike Ultralytics YOLOv8/AGPL). Predicts three heatmap channels:

    NUT   — the two nut endpoints (u=0 line, low-E & high-E edges)
    INLAY — position-inlay dots (frets 3,5,7,9,12,15,17,19,21)
    DOT12 — the 12th-fret DOUBLE dot, the absolute numbering anchor

Post-processing turns heatmap peaks into numbered correspondences that feed
`fretboard.NeckModel.fit_points`. Keypoints (not boxes) mean orientation is
handled by the homography — no oriented-box detector needed.
"""
import os

os.environ.setdefault("KERAS_BACKEND", "torch")

import numpy as np
import cv2
import keras
from keras import layers

from .fretboard import inlay_u, NeckModel

INPUT_SIZE = 224
NUT, INLAY, DOT12 = 0, 1, 2
STD_INLAYS = [3, 5, 7, 9, 12, 15, 17, 19, 21]  # standard dot frets (double dot @12)


def build_model(input_size=INPUT_SIZE):
    """MobileNetV3Small backbone -> upsampling decoder -> 3 heatmap channels."""
    backbone = keras.applications.MobileNetV3Small(
        input_shape=(input_size, input_size, 3), include_top=False,
        weights="imagenet", include_preprocessing=True,
    )
    x = backbone.output  # 7x7 for 224 input
    for filt in (128, 64, 32):  # 7 -> 14 -> 28 -> 56
        x = layers.Conv2DTranspose(filt, 3, strides=2, padding="same", activation="relu")(x)
    heat = layers.Conv2D(3, 1, activation="sigmoid", name="heatmaps")(x)
    return keras.Model(backbone.input, heat, name="fretboard_kps")


def peaks(heat, thresh=0.5, max_pts=12):
    """Local maxima of one heatmap channel -> list of (x, y) centroids."""
    mask = (heat >= thresh).astype(np.uint8)
    n, _, _, cent = cv2.connectedComponentsWithStats(mask, connectivity=8)
    return [(float(cent[i][0]), float(cent[i][1])) for i in range(1, n)][:max_pts]


def number_inlays(nut_lo, nut_hi, inlays, dot12=None):
    """Assign fret numbers to detected inlay dots.

    Order dots along the neck axis (nut -> bridge); anchor absolute numbering on
    the 12th double-dot when visible, else assume the nut-nearest dot is fret 3.
    Returns [(fret, (x, y)), ...].
    ponytail: no-dot12 fallback assumes standard dot layout from the nut; upgrade
    path is an equal-tempered spacing fit when neither nut nor 12th is in frame.
    """
    if not inlays:
        return []
    nut_mid = np.mean([nut_lo, nut_hi], axis=0)
    pts = np.array(inlays, dtype=float)
    axis = pts.mean(axis=0) - nut_mid
    norm = np.linalg.norm(axis)
    if norm < 1e-6:
        return []
    axis /= norm
    order = np.argsort((pts - nut_mid) @ axis)  # near->far from nut
    sorted_pts = pts[order]

    if dot12 is not None:
        r12 = int(np.argmin(np.linalg.norm(sorted_pts - np.array(dot12), axis=1)))
        base = STD_INLAYS.index(12)
    else:
        r12, base = 0, 0  # nut-nearest dot == STD_INLAYS[0] == fret 3
    out = []
    for i, p in enumerate(sorted_pts):
        s = base + (i - r12)
        if 0 <= s < len(STD_INLAYS):
            out.append((STD_INLAYS[s], (float(p[0]), float(p[1]))))
    return out


def correspondences(nut_lo, nut_hi, numbered):
    """Nut endpoints + numbered inlays -> (image_xy, (u, v)) pairs for NeckModel."""
    corr = [(tuple(nut_lo), (0.0, 0.0)), (tuple(nut_hi), (0.0, 1.0))]
    corr += [(p, (inlay_u(n), 0.5)) for n, p in numbered]  # inlays sit mid-neck
    return corr


class Detector:
    """Wraps the model + weights; detect() -> NeckModel-ready correspondences."""

    def __init__(self, weights=None, input_size=INPUT_SIZE):
        self.input_size = input_size
        self.model = build_model(input_size)
        if weights and os.path.exists(weights):
            self.model.load_weights(weights)

    def detect(self, frame_bgr):
        h, w = frame_bgr.shape[:2]
        inp = cv2.resize(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB),
                         (self.input_size, self.input_size))
        heat = self.model.predict(inp[None].astype("float32"), verbose=0)[0]
        hh, hw = heat.shape[:2]
        sx, sy = w / hw, h / hh  # heatmap -> original-frame scale

        def scaled(ch):
            return [(x * sx, y * sy) for x, y in peaks(heat[..., ch])]

        nut = scaled(NUT)
        if len(nut) < 2:
            return None
        nut = sorted(nut, key=lambda p: p[1])  # low-E (top) vs high-E by y
        dots = scaled(INLAY)
        d12 = scaled(DOT12)
        numbered = number_inlays(nut[0], nut[1], dots, d12[0] if d12 else None)
        return correspondences(nut[0], nut[1], numbered)


def _demo():
    # Ground-truth neck->image homography (neck seen at an angle).
    neck_quad = np.float32([(0, 0), (0.6, 0), (0.6, 1), (0, 1)])
    img_quad = np.float32([(100, 100), (500, 120), (480, 300), (120, 340)])
    Hgt = cv2.getPerspectiveTransform(neck_quad, img_quad)

    def to_img(u, v):
        p = cv2.perspectiveTransform(np.float32([[[u, v]]]), Hgt)[0, 0]
        return (float(p[0]), float(p[1]))

    nut_lo, nut_hi = to_img(0, 0), to_img(0, 1)
    frets = [3, 5, 7, 9, 12]
    dots = [to_img(inlay_u(n), 0.5) for n in frets]
    dot12 = to_img(inlay_u(12), 0.5)

    # numbering: anchored on the 12th dot AND the nut-nearest fallback both work.
    assert [n for n, _ in number_inlays(nut_lo, nut_hi, dots, dot12)] == frets
    assert [n for n, _ in number_inlays(nut_lo, nut_hi, dots, None)] == frets

    # correspondences -> homography -> known fingertip reads back correctly.
    m = NeckModel()
    assert m.fit_points(correspondences(nut_lo, nut_hi,
                                        number_inlays(nut_lo, nut_hi, dots, dot12)))
    from .fretboard import fret_u
    assert m.image_to_string_fret(to_img(fret_u(7), 0.4)) == (4, 7)  # string 4, fret 7

    # peak-pick: two synthetic blobs -> two centroids near their centers.
    hm = np.zeros((56, 56), np.float32)
    cv2.circle(hm, (10, 20), 3, 1.0, -1)
    cv2.circle(hm, (40, 30), 3, 1.0, -1)
    found = sorted(peaks(hm))
    assert len(found) == 2 and abs(found[0][0] - 10) < 2 and abs(found[1][0] - 40) < 2

    # model wiring: builds and forward-passes to the expected heatmap shape.
    out = build_model().predict(np.zeros((1, INPUT_SIZE, INPUT_SIZE, 3), "float32"), verbose=0)
    assert out.shape == (1, 56, 56, 3), out.shape
    print("detector self-check OK (numbering + peaks + model wiring)")


if __name__ == "__main__":
    _demo()

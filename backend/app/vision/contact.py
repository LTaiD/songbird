"""Learned monocular press/hover head (spec §C): a single webcam barely separates
a pressed string from a hovering finger, so a small Keras(torch) MLP over the 21
hand landmarks outputs a press probability instead of trusting MediaPipe z.

Untrained (no weights file) it returns a neutral 0.5 so fusion runs end-to-end;
training data (press vs hover labels) is collected later with real footage —
same footage-gated path as the fretboard detector.
"""
import os

os.environ.setdefault("KERAS_BACKEND", "torch")

import numpy as np
import keras
from keras import layers

WEIGHTS = os.path.join(os.path.dirname(__file__), "..", "models", "contact.weights.h5")
N_LANDMARKS = 21


def build_model():
    """(21*3 relative landmark coords) -> press probability."""
    return keras.Sequential([
        keras.Input((N_LANDMARKS * 3,)),
        layers.Dense(64, activation="relu"),
        layers.Dense(32, activation="relu"),
        layers.Dense(1, activation="sigmoid"),
    ], name="contact_head")


def features(hand_landmarks):
    """MediaPipe landmark list -> wrist-relative flattened vector (scale-normed)."""
    pts = np.array([[l.x, l.y, l.z] for l in hand_landmarks], np.float32)
    pts -= pts[0]  # wrist origin
    scale = np.linalg.norm(pts[9]) or 1.0  # wrist->middle-MCP as hand size
    return (pts / scale).reshape(-1)


class ContactHead:
    def __init__(self, weights=WEIGHTS):
        self.model = None
        if os.path.exists(weights):
            self.model = build_model()
            self.model.load_weights(weights)

    def press_prob(self, hand_landmarks):
        if self.model is None:
            return 0.5  # neutral until trained — fusion still runs
        x = features(hand_landmarks)[None]
        return float(self.model.predict(x, verbose=0)[0, 0])


def _demo():
    class L:  # minimal landmark stub
        def __init__(s, x, y, z): s.x, s.y, s.z = x, y, z
    lms = [L(i * 0.01, i * 0.02, 0.0) for i in range(N_LANDMARKS)]
    f = features(lms)
    assert f.shape == (63,) and abs(np.linalg.norm(f[27:30]) - 1.0) < 1e-5  # idx 9 normed
    p = build_model().predict(f[None], verbose=0)
    assert 0.0 <= float(p[0, 0]) <= 1.0
    assert ContactHead(weights="/nonexistent").press_prob(lms) == 0.5
    print("contact self-check OK (features + head + neutral fallback)")


if __name__ == "__main__":
    _demo()

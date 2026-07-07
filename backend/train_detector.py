"""Train the fretboard keypoint detector on auto-labeled frames.

Data: a dir of <name>.png + <name>.json produced by label_from_markers.py.
Targets: gaussian heatmaps for the NUT / INLAY / DOT12 channels.

Run:   python -m backend.train_detector <data_dir> [--epochs N] [--out path]
Smoke: python -m backend.train_detector --smoke   (verifies the loop, no footage)

MPS note: Keras' torch backend runs on CPU here; for a real multi-hundred-frame
train, move to MPS/GPU. The model + loss are small, so CPU is fine for a smoke.
"""
import os
import sys
import glob
import json

os.environ.setdefault("KERAS_BACKEND", "torch")

import numpy as np
import cv2
import keras

from backend.app.vision.detector import build_model, INPUT_SIZE, NUT, INLAY, DOT12

OUT_HM = INPUT_SIZE // 4  # 56
WEIGHTS = "backend/app/models/fretboard_kps.weights.h5"


def _blob(hm, x, y, sigma=1.5):
    xs = np.arange(hm.shape[1])
    ys = np.arange(hm.shape[0])[:, None]
    np.maximum(hm, np.exp(-((xs - x) ** 2 + (ys - y) ** 2) / (2 * sigma ** 2)), out=hm)


def make_target(kp, w, h):
    """Keypoint dict (image coords) -> (OUT_HM, OUT_HM, 3) heatmap target."""
    y = np.zeros((OUT_HM, OUT_HM, 3), np.float32)
    sx, sy = OUT_HM / w, OUT_HM / h
    for p in kp["nut"]:
        _blob(y[..., NUT], p[0] * sx, p[1] * sy)
    for p in kp["inlays"].values():
        _blob(y[..., INLAY], p[0] * sx, p[1] * sy)
    _blob(y[..., DOT12], kp["dot12"][0] * sx, kp["dot12"][1] * sy)
    return y


def load_dataset(data_dir):
    X, Y = [], []
    for jf in sorted(glob.glob(os.path.join(data_dir, "*.json"))):
        img = cv2.imread(jf[:-5] + ".png")
        if img is None:
            continue
        h, w = img.shape[:2]
        kp = json.load(open(jf))
        X.append(cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), (INPUT_SIZE, INPUT_SIZE)))
        Y.append(make_target(kp, w, h))
    if not X:
        raise SystemExit(f"no labeled frames in {data_dir}")
    return np.float32(X), np.float32(Y)


def train(data_dir, epochs=40, out=WEIGHTS):
    X, Y = load_dataset(data_dir)
    model = build_model()
    model.compile(optimizer="adam", loss="mse")
    model.fit(X, Y, epochs=epochs, batch_size=8, validation_split=0.15)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    model.save_weights(out)
    print(f"saved weights -> {out} ({len(X)} frames)")


def _smoke():
    # Two synthetic samples -> build targets -> one training step -> finite loss.
    kp = {"nut": [[40, 30], [40, 210]], "inlays": {"3": [90, 120], "5": [140, 120]},
          "dot12": [200, 120]}
    X = np.random.rand(2, INPUT_SIZE, INPUT_SIZE, 3).astype("float32")
    Y = np.stack([make_target(kp, 320, 240)] * 2)
    assert Y.max() > 0.9  # blobs rendered
    model = build_model()
    model.compile(optimizer="adam", loss="mse")
    hist = model.fit(X, Y, epochs=1, batch_size=2, verbose=0)
    assert np.isfinite(hist.history["loss"][-1])
    print("train_detector smoke OK (heatmap targets + training loop)")


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--smoke" in a:
        _smoke()
    elif a:
        epochs = int(a[a.index("--epochs") + 1]) if "--epochs" in a else 40
        out = a[a.index("--out") + 1] if "--out" in a else WEIGHTS
        train(a[0], epochs, out)
    else:
        raise SystemExit(__doc__)

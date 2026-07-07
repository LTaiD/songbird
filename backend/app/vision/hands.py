"""MediaPipe Hand Landmarker (Tasks API) wrapper.

Returns fretting-hand fingertip pixels per frame. Auto-downloads the model on
first run so there's no manual setup step.
"""
import os
import urllib.request

import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
_MODEL_PATH = os.path.join(os.path.dirname(__file__), "hand_landmarker.task")

# fingertip landmark indices: thumb, index, middle, ring, pinky.
# ponytail: thumb (4) IS a fretting finger — thumb-over the low E (Hendrix chords).
# The picking-hand thumb (Travis picking) lands past the 12th-fret marker, so the
# board filter drops it here; its pluck-event detection is Phase 5 (righthand.py).
FINGERTIPS = (4, 8, 12, 16, 20)


def _ensure_model():
    if not os.path.exists(_MODEL_PATH):
        urllib.request.urlretrieve(_MODEL_URL, _MODEL_PATH)
    return _MODEL_PATH


class HandTracker:
    def __init__(self, num_hands=2):
        opts = mp_vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=_ensure_model()),
            num_hands=num_hands,
            running_mode=mp_vision.RunningMode.VIDEO,
        )
        self._lm = mp_vision.HandLandmarker.create_from_options(opts)

    def fingertips(self, frame_rgb, timestamp_ms, w, h):
        """Yield (x_px, y_px) for every fingertip of every detected hand.

        ponytail: Phase 0 overlays all hands, not just the fretting one — the
        board homography already filters tips to on-fretboard ones. Handedness
        gating comes with the real pipeline (Phase 2).
        """
        img = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        res = self._lm.detect_for_video(img, timestamp_ms)
        for hand in res.hand_landmarks:
            for i in FINGERTIPS:
                yield hand[i].x * w, hand[i].y * h

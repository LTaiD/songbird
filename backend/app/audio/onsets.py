"""Audio onset detection — the WHEN of the transcription (librosa, whole clip).

Batch two-pass: librosa's spectral-flux onset detector with backtracking to the
preceding energy minimum so onset times sit at note starts, not peak energy.
"""
import numpy as np
import librosa

SR = 22050


def load(path, sr=SR):
    y, _ = librosa.load(path, sr=sr, mono=True)
    return y


def detect(y, sr=SR):
    """Return onset times (seconds, ascending) for a whole clip."""
    return librosa.onset.onset_detect(y=y, sr=sr, units="time", backtrack=True)


def _demo():
    # Synthesize 4 plucks (decaying 220 Hz bursts) at known times.
    sr, times = SR, [0.5, 1.0, 1.5, 2.25]
    y = np.zeros(int(3 * sr), np.float32)
    for t in times:
        n = int(0.3 * sr)
        i = int(t * sr)
        burst = np.sin(2 * np.pi * 220 * np.arange(n) / sr) * np.exp(-np.arange(n) / (0.05 * sr))
        y[i:i + n] += burst.astype(np.float32)
    got = detect(y, sr)
    assert len(got) == 4, got
    assert all(abs(g - t) < 0.06 for g, t in zip(got, times)), got
    print("onsets self-check OK", np.round(got, 3))


if __name__ == "__main__":
    _demo()

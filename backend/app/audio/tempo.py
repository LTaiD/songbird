"""Tempo / beat grid. The metronome default collapses this from estimation to
grid-snapping (spec §D.5): if the user played to a known BPM, build the grid
from it; free-tempo falls back to librosa's whole-clip estimate.
"""
import numpy as np
import librosa


def beat_grid(known_bpm=None, y=None, sr=22050, duration=None):
    """Return (bpm, grid_times). Known metronome tempo wins; else estimate."""
    if known_bpm:
        bpm = float(known_bpm)
        dur = duration if duration is not None else len(y) / sr
    else:
        bpm = float(np.atleast_1d(librosa.beat.tempo(y=y, sr=sr))[0])
        dur = len(y) / sr
    step = 60.0 / bpm
    return bpm, np.arange(0.0, dur + step, step)


def _demo():
    bpm, grid = beat_grid(known_bpm=120, duration=4.0)
    assert bpm == 120 and abs(grid[1] - 0.5) < 1e-9 and grid[-1] >= 4.0
    # estimation path: clicks at 120 bpm
    sr = 22050
    y = np.zeros(6 * sr, np.float32)
    for i in range(12):
        j = int(i * 0.5 * sr)
        y[j:j + 200] = np.random.default_rng(i).uniform(-1, 1, 200).astype(np.float32)
    est, _ = beat_grid(y=y, sr=sr)
    assert 100 < est < 140, est  # librosa lands near 120 (octave errors excluded)
    print(f"tempo self-check OK (known=120, estimated={est:.1f})")


if __name__ == "__main__":
    _demo()

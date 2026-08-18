import numpy as np

from .audio import SR
from .embed import embed_windows


def windows(wav, win_s=10, hop_s=5):
    win = int(win_s * SR)
    hop = int(hop_s * SR)
    n = len(wav)
    if n <= win:
        yield wav
        return
    start = 0
    while start + win <= n:
        yield wav[start:start + win]
        start += hop


def embed_all(wav, win_s=10, hop_s=5):
    return embed_windows(list(windows(wav, win_s, hop_s))).astype(np.float32)


def _demo():
    win_s, hop_s = 10, 5
    win, hop = int(win_s * SR), int(hop_s * SR)
    for n_windows in (1, 3, 7):
        n = win + (n_windows - 1) * hop + hop // 2
        wav = np.zeros(n, dtype=np.float32)
        got = sum(1 for _ in windows(wav, win_s, hop_s))
        expected = (n - win) // hop + 1
        assert got == expected == n_windows, (n, got, expected)
    short = np.zeros(win // 2, dtype=np.float32)
    assert sum(1 for _ in windows(short, win_s, hop_s)) == 1
    print("windowing.py ok")


if __name__ == "__main__":
    _demo()

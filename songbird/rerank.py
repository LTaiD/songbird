import json
import re
import urllib.parse
import urllib.request

import librosa
import numpy as np

from .audio import SR, load

FPS = 5
STOP = {"the", "and", "a", "of"}


def chroma_seq(wav):
    hop = SR // FPS
    c = librosa.feature.chroma_cqt(y=wav, sr=SR, hop_length=hop)
    c = c / (np.linalg.norm(c, axis=0, keepdims=True) + 1e-8)
    return c.T.astype(np.float32)


def align_score(qc, rc, gap=0.4):
    tq = len(qc)
    best = -1e9
    for sh in range(12):
        s = (np.roll(rc, sh, axis=1) @ qc.T) - 0.5
        prev = np.zeros(tq, np.float32)
        mx = 0.0
        for i in range(len(rc)):
            diag = np.empty(tq, np.float32)
            diag[0] = 0.0
            diag[1:] = prev[:-1]
            cur = np.maximum(0.0, np.maximum(diag + s[i], prev - gap))
            m = cur.max()
            if m > mx:
                mx = m
            prev = cur
        best = max(best, mx / len(rc))
    return best


def _norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s.lower())).strip()


def _atoken(a):
    for t in _norm(a).split():
        if t not in STOP:
            return t
    return _norm(a)


def preview_url(song, artist):
    url = "https://itunes.apple.com/search?" + urllib.parse.urlencode(
        {"term": f"{artist} {song}", "entity": "song", "limit": 8, "country": "US"})
    req = urllib.request.Request(url, headers={"User-Agent": "songbird-rerank/1.0"})
    try:
        res = json.load(urllib.request.urlopen(req, timeout=20)).get("results", [])
    except Exception:
        return None
    for r in res:
        if (r.get("previewUrl") and _norm(song) in _norm(r.get("trackName", ""))
                and _atoken(artist) in _norm(r.get("artistName", ""))):
            return r["previewUrl"]
    return None


def chroma_rerank(query_wav, candidates):
    qc = chroma_seq(query_wav)
    scored = []
    for song, artist in candidates:
        url = preview_url(song, artist)
        if not url:
            continue
        try:
            sc = align_score(qc, chroma_seq(load(url)))
        except Exception:
            continue
        scored.append(((song, artist), sc))
    if not scored:
        return None
    scored.sort(key=lambda x: -x[1])
    return scored


def _demo():
    rng = np.random.default_rng(0)
    t = np.linspace(0, 6, int(6 * SR), endpoint=False)
    prog = np.concatenate([np.sin(2 * np.pi * f * t[: int(1.5 * SR)]) for f in (261.6, 349.2, 392.0, 293.7)])
    a = chroma_seq(prog.astype(np.float32))
    b = chroma_seq((prog + 0.05 * rng.standard_normal(len(prog))).astype(np.float32))
    other = chroma_seq(np.sin(2 * np.pi * 440 * t).astype(np.float32))
    assert align_score(a, b) > align_score(a, other), "same progression should align better"
    print("rerank.py ok")


if __name__ == "__main__":
    _demo()

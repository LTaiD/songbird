import math
from collections import defaultdict

import numpy as np

from . import index as index_mod
from .audio import load as load_audio
from .windowing import embed_all


def match_matrix(query, index, rows, k=3, tau=0.1, keep=0.33, min_windows=8):
    if index.ntotal == 0 or len(query) == 0:
        return None
    k = min(k, index.ntotal)
    query = np.ascontiguousarray(query, dtype=np.float32)
    sims, ids = index.search(query, k)
    order = np.argsort(-sims[:, 0])
    n = len(order)
    if n > min_windows and 0.0 < keep < 1.0:
        sel = order[:max(min_windows, int(round(keep * n)))]
    else:
        sel = order
    scores = defaultdict(float)
    for wi in sel:
        for s, i in zip(sims[wi], ids[wi]):
            if i < 0:
                continue
            song, artist = rows[i][0], rows[i][1]
            scores[(song, artist)] += math.exp(float(s) / tau)
    if not scores:
        return None
    return max(scores, key=scores.get)


def match_topk(query, index, rows, k=3, tau=0.1, recall_k=12, keep=0.33, min_windows=8):
    if index.ntotal == 0 or len(query) == 0:
        return []
    k = min(k, index.ntotal)
    query = np.ascontiguousarray(query, dtype=np.float32)
    sims, ids = index.search(query, k)
    order = np.argsort(-sims[:, 0])
    n = len(order)
    sel = order[:max(min_windows, int(round(keep * n)))] if (n > min_windows and 0.0 < keep < 1.0) else order
    scores = defaultdict(float)
    for wi in sel:
        for s, i in zip(sims[wi], ids[wi]):
            if i < 0:
                continue
            scores[(rows[i][0], rows[i][1])] += math.exp(float(s) / tau)
    return [c for c, _ in sorted(scores.items(), key=lambda kv: -kv[1])[:recall_k]]


def _apple_url(rows, pred):
    for r in rows:
        if (r[0], r[1]) == pred and len(r) > 2 and r[2]:
            return r[2]
    return ""


def match(audio_path, data_dir="data/catalog", k=3, tau=0.1, win_s=10, hop_s=5,
          rerank=True, recall_k=12):
    from .activity import trim_to_music
    from .rerank import chroma_rerank
    index, rows = index_mod.load(data_dir)
    wav = trim_to_music(load_audio(audio_path))
    cands = match_topk(embed_all(wav, win_s, hop_s), index, rows, k, tau, recall_k)
    if not cands:
        return None
    pred = cands[0]
    if rerank and len(cands) > 1:
        try:
            rr = chroma_rerank(wav, cands)
            if rr:
                pred = rr[0][0]
        except Exception:
            pass
    return pred[0], pred[1], _apple_url(rows, pred)


def _demo():
    rng = np.random.default_rng(1)
    a = rng.standard_normal((5, 16)).astype(np.float32)
    a /= np.linalg.norm(a, axis=1, keepdims=True)
    b = rng.standard_normal((5, 16)).astype(np.float32)
    b /= np.linalg.norm(b, axis=1, keepdims=True)
    m = np.concatenate([a, b], axis=0)
    rows = [["A", "x"]] * 5 + [["B", "y"]] * 5
    idx = index_mod.build(m)

    query = a[:3] + 0.01 * rng.standard_normal((3, 16)).astype(np.float32)
    query /= np.linalg.norm(query, axis=1, keepdims=True)
    assert match_matrix(query, idx, rows, k=3) == ("A", "x")

    empty = index_mod.build(np.zeros((0, 16), dtype=np.float32))
    assert match_matrix(query, empty, [], k=5) is None
    print("matcher.py ok")


if __name__ == "__main__":
    _demo()

import os
import pickle

import numpy as np

from .rerank import chroma_seq, align_score

_cache = {}


def load_store(data_dir):
    p = os.path.join(data_dir, "chroma.pkl")
    if not os.path.exists(p):
        return None
    mt = os.path.getmtime(p)
    if _cache.get("path") != p or _cache.get("mt") != mt:
        d = pickle.load(open(p, "rb"))
        _cache.update(path=p, mt=mt, store=d["store"])
    return _cache["store"]


def _coarse(a):
    m = a.mean(axis=0)
    n = np.linalg.norm(m)
    return m / n if n > 0 else m


def _gate(scored, muq_cands, margin):
    muq = set(muq_cands)
    in_muq = [s for s in scored if s[0] in muq]
    if scored and scored[0][0] not in muq and in_muq and scored[0][1] - in_muq[0][1] < margin:
        return in_muq + [s for s in scored if s[0] not in muq]
    return scored


def fuse(query_wav, data_dir, muq_cands, prefilter=90, margin=0.05):
    store = load_store(data_dir)
    if not store:
        return None
    qc = chroma_seq(query_wav)
    qm = _coarse(qc)
    coarse = [(k, max(float(qm @ np.roll(_coarse(a), sh)) for sh in range(12))) for k, a in store.items()]
    coarse.sort(key=lambda x: -x[1])
    pool = list(dict.fromkeys(list(muq_cands) + [k for k, _ in coarse[:prefilter]]))
    scored = [(k, align_score(qc, store[k])) for k in pool if k in store]
    if not scored:
        return None
    scored.sort(key=lambda x: -x[1])
    return _gate(scored, muq_cands, margin)


def _demo():
    A, B, C = ("a", "x"), ("b", "y"), ("c", "z")
    muq = [A, B]
    s1 = sorted([(C, 0.40), (A, 0.38), (B, 0.30)], key=lambda x: -x[1])
    assert _gate(s1, muq, 0.05)[0][0] == A
    assert _gate(s1, muq, 0.01)[0][0] == C
    s2 = sorted([(A, 0.40), (C, 0.39)], key=lambda x: -x[1])
    assert _gate(s2, muq, 0.05)[0][0] == A
    assert _gate([], muq, 0.05) == []
    print("chroma_index.py ok")


if __name__ == "__main__":
    _demo()

import json
import os

import torch
import faiss
import numpy as np

faiss.omp_set_num_threads(1)


def build(matrix):
    matrix = np.ascontiguousarray(matrix, dtype=np.float32)
    index = faiss.IndexFlatIP(matrix.shape[1])
    index.add(matrix)
    return index


def save(index, rows, out_dir="data"):
    os.makedirs(out_dir, exist_ok=True)
    faiss.write_index(index, os.path.join(out_dir, "index.faiss"))
    with open(os.path.join(out_dir, "index_map.json"), "w") as f:
        json.dump(rows, f)


def load(out_dir="data"):
    index = faiss.read_index(os.path.join(out_dir, "index.faiss"))
    with open(os.path.join(out_dir, "index_map.json")) as f:
        rows = json.load(f)
    return index, rows


def _demo():
    import tempfile

    rng = np.random.default_rng(0)
    m = rng.standard_normal((6, 32)).astype(np.float32)
    m /= np.linalg.norm(m, axis=1, keepdims=True)
    rows = [["Song A", "Artist 1"]] * 3 + [["Song B", "Artist 2"]] * 3

    idx = build(m)
    assert idx.ntotal == 6
    d = tempfile.mkdtemp()
    save(idx, rows, d)
    idx2, rows2 = load(d)
    assert idx2.ntotal == 6 and rows2 == rows
    sims, ids = idx2.search(m[:1], 1)
    assert ids[0][0] == 0 and abs(sims[0][0] - 1.0) < 1e-4
    print("index.py ok")


if __name__ == "__main__":
    _demo()

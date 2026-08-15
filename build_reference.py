import csv
import os
import sys

import numpy as np

from songbird import index as index_mod
from songbird.audio import load
from songbird.windowing import embed_all


def build_reference(ref_dir="reference", data_dir="data", win_s=10, hop_s=5):
    meta_path = os.path.join(ref_dir, "metadata.csv")
    vectors = []
    rows = []
    with open(meta_path, newline="") as f:
        for r in csv.DictReader(f):
            wav = load(os.path.join(ref_dir, r["filename"]))
            mat = embed_all(wav, int(win_s), int(hop_s))
            vectors.append(mat)
            rows.extend([[r["song"], r["artist"]] for _ in range(len(mat))])
    if not vectors:
        raise SystemExit("no reference audio in " + meta_path)
    matrix = np.concatenate(vectors, axis=0)
    index_mod.save(index_mod.build(matrix), rows, data_dir)
    print("indexed", len(rows), "windows ->", data_dir)


if __name__ == "__main__":
    build_reference(*sys.argv[1:])

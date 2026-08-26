#!/usr/bin/env python3
import glob
import json
import os
import pickle
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "data", "catalog", "manifest.json")
CHROMA = os.path.join(ROOT, "data", "catalog", "chroma.pkl")


def find_log():
    if len(sys.argv) > 1:
        return sys.argv[1]
    local = os.path.join(ROOT, "scratchpad", "chroma.log")
    if os.path.exists(local):
        return local
    cands = glob.glob("/private/tmp/claude-*/**/tasks/*.output", recursive=True)
    best, bestmt = None, -1
    for c in cands:
        try:
            txt = open(c, errors="replace").read()
        except Exception:
            continue
        if "tracks to resolve" in txt or "to fingerprint" in txt:
            mt = os.path.getmtime(c)
            if mt > bestmt:
                best, bestmt = c, mt
    return best


def counts():
    done = chr_n = 0
    try:
        m = json.load(open(MANIFEST))
        done = sum(1 for v in m.values() if v == "done")
    except Exception:
        pass
    try:
        chr_n = len(pickle.load(open(CHROMA, "rb"))["store"])
    except Exception:
        pass
    return done, chr_n


def bar(frac, width=34):
    frac = max(0.0, min(1.0, frac))
    fill = int(round(frac * width))
    return "[" + "#" * fill + "-" * (width - fill) + f"] {frac * 100:5.1f}%"


def main():
    log = find_log()
    while True:
        txt = ""
        if log and os.path.exists(log):
            txt = open(log, errors="replace").read()
        done, chr_n = counts()
        if "CHAIN EXIT" in txt or "DONE " in txt.split("starting chroma")[-1]:
            m = re.findall(r"DONE (\d+) stored", txt)
            sys.stdout.write("\r" + " " * 78 + "\r")
            print(f"DONE  catalog songs={done}  chroma stored={chr_n}")
            return
        if "starting chroma" in txt:
            tot = re.findall(r"(\d+) to fingerprint of (\d+)", txt)
            cur = re.findall(r"(\d+)/(\d+)\s*$", txt.strip().splitlines()[-1]) if txt.strip() else []
            total = int(tot[-1][0]) if tot else 1
            i = int(re.findall(r", (\d+)/\d+", txt)[-1]) if re.findall(r", (\d+)/\d+", txt) else 0
            line = f"CHROMA  {bar(i / total)}  {i}/{total}  stored={chr_n}"
        else:
            b = re.findall(r"batch through (\d+)/(\d+)", txt)
            if b:
                i, total = int(b[-1][0]), int(b[-1][1])
                line = f"CATALOG {bar(i / total)}  {i}/{total} tracks  songs={done}"
            else:
                line = f"CATALOG starting...  songs={done}"
        sys.stdout.write("\r" + line + " " * max(0, 78 - len(line)))
        sys.stdout.flush()
        time.sleep(2)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()

#!/usr/bin/env python3
import glob
import os
import statistics
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from songbird.matcher import match

URLS = [
    "https://www.youtube.com/watch?v=4iHV1znFRwk",
    "https://www.youtube.com/watch?v=fWU1yZnesKs",
    "https://www.youtube.com/watch?v=FgyAFFoCAdc",
]

GROUND_TRUTH = {
    "https://www.youtube.com/watch?v=4iHV1znFRwk": ["Here", "Pavement"],
    "https://www.youtube.com/watch?v=fWU1yZnesKs": ["Tomorrow Never Knows", "The Beatles"],
    "https://www.youtube.com/watch?v=FgyAFFoCAdc": ["Out the Door", "Congress The Band"],
}

CONFIGS = {
    "cap": {"max_seconds": 90, "recall_k": 5},
    "full": {"max_seconds": None, "recall_k": 12},
}


def _register_components():
    try:
        from yt_dlp.globals import supported_remote_components
        for c in ("ejs:github", "ejs:npm"):
            if c not in supported_remote_components.value:
                supported_remote_components.value.append(c)
    except Exception:
        pass


def _download(url, tmpdir, n, attempts=3):
    import yt_dlp
    _register_components()
    base = os.path.join(tmpdir, f"q{n}")
    opts = {
        "format": "bestaudio/best", "quiet": True, "noplaylist": True,
        "cachedir": False, "retries": 3, "fragment_retries": 3,
        "remote_components": ["ejs:github"], "outtmpl": base + ".%(ext)s",
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}],
    }
    last = None
    for _ in range(attempts):
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            hits = glob.glob(base + ".wav") or glob.glob(base + ".*")
            if hits:
                return hits[0]
        except Exception as exc:
            last = exc
    raise RuntimeError(f"no audio downloaded after {attempts} tries ({last})")


def _report(rows):
    print()
    print(f"{'query':<7}{'config':<7}{'elapsed':>9}  {'correct':<8}prediction")
    print("-" * 72)
    per_cfg = {c: {"t": [], "n": 0, "ok": 0} for c in CONFIGS}
    for q, cfg, elapsed, got, correct in rows:
        pred = "-" if got == (None, None) else f"{got[1]} — {got[0]}"
        et = "err" if elapsed is None else f"{elapsed:>7.1f}s"
        print(f"{q:<7}{cfg:<7}{et:>9}  {str(correct):<8}{pred}")
        if elapsed is not None and cfg in per_cfg:
            per_cfg[cfg]["t"].append(elapsed)
            per_cfg[cfg]["n"] += 1
            per_cfg[cfg]["ok"] += 1 if correct else 0
    print("-" * 72)
    for cfg, s in per_cfg.items():
        if not s["n"]:
            continue
        acc = 100.0 * s["ok"] / s["n"]
        print(f"{cfg:<7} accuracy {acc:5.1f}%  "
              f"mean {statistics.mean(s['t']):5.1f}s  "
              f"median {statistics.median(s['t']):5.1f}s  (n={s['n']})")


def main():
    if not GROUND_TRUTH:
        print("Set GROUND_TRUTH = {url: [song, artist]} for these URLs, then re-run:")
        for u in URLS:
            print("  ", u)
        return 1
    tmpdir = tempfile.mkdtemp(prefix="bench_")
    rows = []
    for n, url in enumerate(URLS, 1):
        try:
            path = _download(url, tmpdir, n)
        except Exception as exc:
            print(f"q{n} download failed: {exc}")
            continue
        if not os.path.basename(path).startswith(f"q{n}"):
            raise AssertionError("blind guardrail: query filename carries metadata")
        for cfg_name, cfg in CONFIGS.items():
            t0 = time.time()
            try:
                pred = match(path, max_seconds=cfg["max_seconds"], recall_k=cfg["recall_k"])
                elapsed = round(time.time() - t0, 1)
            except Exception as exc:
                rows.append((f"q{n}", cfg_name, None, (None, None), f"ERR {exc}"))
                continue
            got = (pred[0], pred[1]) if pred else (None, None)
            gt = tuple(GROUND_TRUTH.get(url) or (None, None))
            correct = bool(pred) and got == gt
            rows.append((f"q{n}", cfg_name, elapsed, got, correct))
    _report(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())

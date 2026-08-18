#!/usr/bin/env python3
import json
import os
import sys
import time

import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from yt_dlp.globals import supported_remote_components
    for _c in ("ejs:github", "ejs:npm"):
        if _c not in supported_remote_components.value:
            supported_remote_components.value.append(_c)
except Exception:
    pass

CONFIGS = {
    "cap": {"max_seconds": 90, "recall_k": 5},
    "full": {"max_seconds": None, "recall_k": 12},
}


def _resolve_audio_url(page_url):
    import yt_dlp
    opts = {"format": "bestaudio/best", "quiet": True, "noplaylist": True,
            "cachedir": False, "remote_components": ["ejs:github"]}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(page_url, download=False)
    auds = [f for f in info.get("formats", [])
            if f.get("acodec") not in (None, "none")
            and f.get("vcodec") in (None, "none") and f.get("url")]
    auds.sort(key=lambda f: (str(f.get("protocol", "")).startswith("m3u8"),
                             f.get("abr") or 1e9))
    return auds[0]["url"] if auds else info["url"]


def _handle(req):
    from songbird.matcher import match
    cfg = CONFIGS.get(req.get("config", "full"), CONFIGS["full"])
    src = req["src"]
    if req.get("is_url"):
        src = _resolve_audio_url(src)
    t0 = time.time()
    pred = match(src, max_seconds=cfg["max_seconds"], recall_k=cfg["recall_k"])
    elapsed = round(time.time() - t0, 2)
    if not pred:
        return {"ok": True, "song": None, "artist": None, "apple_url": None, "elapsed": elapsed}
    song, artist, apple_url = pred
    return {"ok": True, "song": song, "artist": artist, "apple_url": apple_url, "elapsed": elapsed}


def _emit(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def main():
    try:
        torch.set_num_threads(max(1, os.cpu_count() or 2))
    except Exception:
        pass
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception as exc:
            _emit({"ok": False, "error": f"bad request: {exc}"})
            continue
        rid = req.get("id")
        try:
            res = _handle(req)
        except Exception as exc:
            res = {"ok": False, "error": str(exc)}
        if rid is not None:
            res["id"] = rid
        _emit(res)


if __name__ == "__main__":
    main()

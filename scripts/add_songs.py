import glob
import json
import os
import sys
import tempfile
import urllib.parse
import urllib.request

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from songbird.audio import load
from songbird.windowing import embed_all
import faiss

OUT = "data/catalog"

ADDS = [
    ("Tomorrow Never Knows", "The Beatles", ("itunes", "The Beatles Tomorrow Never Knows"), ""),
    ("Out the Door", "Congress The Band", ("youtube", "https://www.youtube.com/watch?v=h8X0jlvlKwg"), ""),
]


def _norm(s):
    return "".join(ch for ch in s.lower() if ch.isalnum() or ch == " ").strip()


def _itunes_preview(song, term):
    url = "https://itunes.apple.com/search?" + urllib.parse.urlencode(
        {"term": term, "entity": "song", "limit": 15, "country": "US"})
    req = urllib.request.Request(url, headers={"User-Agent": "songbird/1.0"})
    results = json.load(urllib.request.urlopen(req, timeout=30)).get("results", [])
    for r in results:
        if r.get("previewUrl") and _norm(r.get("trackName", "")) == _norm(song):
            return r["previewUrl"], r.get("trackViewUrl", "")
    for r in results:
        if r.get("previewUrl") and _norm(song) in _norm(r.get("trackName", "")):
            return r["previewUrl"], r.get("trackViewUrl", "")
    raise RuntimeError("no iTunes preview for " + song)


def _youtube_wav(url, tmpdir):
    import yt_dlp
    try:
        from yt_dlp.globals import supported_remote_components
        for c in ("ejs:github", "ejs:npm"):
            if c not in supported_remote_components.value:
                supported_remote_components.value.append(c)
    except Exception:
        pass
    base = os.path.join(tmpdir, "ref")
    opts = {"format": "bestaudio/best", "quiet": True, "noplaylist": True,
            "cachedir": False, "remote_components": ["ejs:github"],
            "outtmpl": base + ".%(ext)s",
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}]}
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    hits = glob.glob(base + ".wav") or glob.glob(base + ".*")
    if not hits:
        raise RuntimeError("no audio downloaded from " + url)
    return hits[0]


def main():
    index = faiss.read_index(os.path.join(OUT, "index.faiss"))
    rows = json.load(open(os.path.join(OUT, "index_map.json")))
    manifest = json.load(open(os.path.join(OUT, "manifest.json")))
    existing = {(r[0], r[1]) for r in rows}
    tmpdir = tempfile.mkdtemp(prefix="addref_")
    for song, artist, (kind, ref), apple in ADDS:
        if (song, artist) in existing:
            print(f"skip (already present): {artist} — {song}", flush=True)
            continue
        if kind == "itunes":
            src, apple = _itunes_preview(song, ref)
        else:
            src = _youtube_wav(ref, tmpdir)
        m = embed_all(load(src))
        index.add(np.ascontiguousarray(m, dtype=np.float32))
        rows.extend([[song, artist, apple] for _ in range(len(m))])
        manifest[_norm(artist) + "|" + _norm(song)] = "done"
        print(f"added {artist} — {song}: {len(m)} windows ({index.ntotal} vectors)", flush=True)
    faiss.write_index(index, os.path.join(OUT, "index.faiss"))
    json.dump(rows, open(os.path.join(OUT, "index_map.json"), "w"))
    json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w"))
    print("saved ->", OUT, flush=True)


if __name__ == "__main__":
    main()

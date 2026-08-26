import json
import os
import pickle
import time
import urllib.error
import urllib.parse
import urllib.request

from songbird.rerank import chroma_seq, _base, _norm, _atoken
from songbird.audio import load

OUT = "data/catalog"
PKL = os.path.join(OUT, "chroma.pkl")
EVERY = 20
RATE = object()


def load_store():
    if os.path.exists(PKL):
        d = pickle.load(open(PKL, "rb"))
        return d["store"], d["skipped"]
    return {}, set()


def save_store(store, skipped):
    pickle.dump({"store": store, "skipped": skipped}, open(PKL, "wb"))


def preview(song, artist):
    b = _base(song) or song
    url = "https://itunes.apple.com/search?" + urllib.parse.urlencode(
        {"term": f"{artist} {b}", "entity": "song", "limit": 12, "country": "US"})
    req = urllib.request.Request(url, headers={"User-Agent": "songbird-rerank/1.0"})
    delay = 5.0
    for attempt in range(6):
        try:
            res = json.load(urllib.request.urlopen(req, timeout=20)).get("results", [])
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                if attempt < 5:
                    time.sleep(delay)
                    delay *= 2
                    continue
                return RATE
            return None
        except Exception:
            return None
        want = set(_norm(b).split()) or set(_norm(song).split())
        for r in res:
            track = set(_norm(r.get("trackName", "")).split())
            if (r.get("previewUrl") and want and want <= track
                    and _atoken(artist) in _norm(r.get("artistName", ""))):
                return r["previewUrl"]
        return None
    return RATE


def main():
    rows = json.load(open(os.path.join(OUT, "index_map.json")))
    songs, seen = [], set()
    for r in rows:
        k = (r[0], r[1])
        if k not in seen:
            seen.add(k)
            songs.append(k)
    store, skipped = load_store()
    todo = [k for k in songs if k not in store and k not in skipped]
    print(f"{len(todo)} to fingerprint of {len(songs)} songs", flush=True)
    n = 0
    for i, (song, artist) in enumerate(todo):
        u = preview(song, artist)
        if u is RATE:
            save_store(store, skipped)
            print(f"rate-limited at {i}/{len(todo)}, saved; re-run to resume", flush=True)
            return
        if not u:
            skipped.add((song, artist))
        else:
            try:
                store[(song, artist)] = chroma_seq(load(u))
            except Exception:
                skipped.add((song, artist))
        n += 1
        if n % EVERY == 0:
            save_store(store, skipped)
            print(f"{len(store)} stored, {len(skipped)} skipped, {i + 1}/{len(todo)}", flush=True)
        time.sleep(30 if n % 30 == 0 else 4.0)
    save_store(store, skipped)
    print(f"DONE {len(store)} stored, {len(skipped)} skipped, of {len(songs)} songs")


if __name__ == "__main__":
    main()

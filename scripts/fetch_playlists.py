#!/usr/bin/env python3
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAYLISTS = os.path.join(ROOT, "data", "playlists.txt")
OUT = os.path.join(ROOT, "data", "editorial_tracks.txt")
MANIFEST = os.path.join(ROOT, "data", "catalog", "manifest.json")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
JWT_RE = re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
STOP = {"the", "and", "a", "of"}


def _get(url, headers=None, timeout=30):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s.lower())).strip()


def atoken(a):
    for t in norm(a).split():
        if t not in STOP:
            return t
    return norm(a)


def base(s):
    return re.sub(r"\s*[\(\[].*", "", s).strip() or s


def fkey(artist, title):
    return atoken(artist) + "|" + norm(base(title))


def get_token():
    html = _get("https://music.apple.com/us/browse")
    m = JWT_RE.search(html)
    if m:
        return m.group(0)
    for js in re.findall(r'src="(/assets/[^"]+\.js)"', html):
        try:
            body = _get("https://music.apple.com" + js)
        except Exception:
            continue
        m = JWT_RE.search(body)
        if m:
            return m.group(0)
    raise RuntimeError("no web-player token found")


def playlist_id(url):
    m = re.search(r"pl\.[A-Za-z0-9]+", url)
    return m.group(0) if m else None


def fetch_tracks(pid, token):
    hdr = {"Authorization": "Bearer " + token, "Origin": "https://music.apple.com",
           "User-Agent": UA}
    out, offset = [], 0
    while True:
        q = urllib.parse.urlencode({"limit": 100, "offset": offset, "l": "en-US"})
        url = f"https://amp-api.music.apple.com/v1/catalog/us/playlists/{pid}/tracks?{q}"
        for attempt in range(5):
            try:
                data = json.loads(_get(url, hdr))
                break
            except urllib.error.HTTPError as e:
                if e.code in (429, 403) and attempt < 4:
                    time.sleep(3 * (attempt + 1))
                    continue
                return out
            except Exception:
                return out
        items = data.get("data", [])
        for it in items:
            a = it.get("attributes", {})
            name, artist = a.get("name"), a.get("artistName")
            if name and artist:
                out.append((artist.strip(), name.strip()))
        if not items or not data.get("next"):
            break
        offset += len(items)
        time.sleep(0.5)
    return out


def load_manifest_keys():
    if not os.path.exists(MANIFEST):
        return set()
    m = json.load(open(MANIFEST))
    keys = set()
    for k in m:
        if "|" in k:
            a, t = k.split("|", 1)
            keys.add(atoken(a) + "|" + norm(base(t)))
    return keys


def read_playlists():
    rows = []
    for line in open(PLAYLISTS, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 4:
            continue
        genre, sub, name, url = parts[0], parts[1], parts[2], parts[3]
        pid = playlist_id(url)
        if pid:
            rows.append((genre, sub, name, pid))
    return rows


def main():
    single = None
    for a in sys.argv[1:]:
        if a.startswith("--playlist="):
            single = a.split("=", 1)[1]
    token = get_token()
    print("token ok:", token[:12] + "...", flush=True)
    if single:
        pid = playlist_id(single) or single
        tr = fetch_tracks(pid, token)
        print(f"{pid}: {len(tr)} tracks")
        for artist, title in tr[:10]:
            print(f"  {artist} | {title}")
        return
    known = load_manifest_keys()
    seen, kept = set(), []
    counts = {}
    for genre, sub, name, pid in read_playlists():
        tr = fetch_tracks(pid, token)
        counts[name] = len(tr)
        print(f"{genre}/{sub} {name} ({pid}): {len(tr)} tracks", flush=True)
        for artist, title in tr:
            fk = fkey(artist, title)
            if fk in seen or fk in known:
                continue
            seen.add(fk)
            kept.append((artist, title))
        time.sleep(1.0)
    with open(OUT, "w", encoding="utf-8") as f:
        for artist, title in kept:
            f.write(f"{artist}|{title}\n")
    print(f"\nnet-new tracks: {len(kept)} -> {OUT}")


def _demo():
    sample = {"data": [
        {"attributes": {"name": "She's Leaving You", "artistName": "MJ Lenderman"}},
        {"attributes": {"name": "Here (Live)", "artistName": "Pavement"}},
        {"attributes": {"name": "no artist"}},
    ], "next": None}
    got = []
    for it in sample["data"]:
        a = it.get("attributes", {})
        if a.get("name") and a.get("artistName"):
            got.append((a["artistName"], a["name"]))
    assert got == [("MJ Lenderman", "She's Leaving You"), ("Pavement", "Here (Live)")]
    assert fkey("The Beatles", "Here Comes the Sun (Remastered 2009)") == "beatles|here comes the sun"
    assert playlist_id("https://music.apple.com/us/playlist/x/pl.abc123DEF") == "pl.abc123DEF"
    print("fetch_playlists.py ok")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        _demo()
    else:
        main()

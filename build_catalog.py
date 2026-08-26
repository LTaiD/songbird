import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import numpy as np

from songbird import index as index_mod
from songbird.audio import load
from songbird.windowing import embed_all
import faiss

OUT = "data/catalog"
CHECKPOINT_EVERY = 10
SONGS_PER_ARTIST = 20
EXCLUDE_GENRES = {"dance", "electronic", "house", "techno", "edm", "dubstep", "trance"}
LIVE_KW = ("live", "unplugged", "concert", " live at", "live from", "live in", "in concert")
STOP = {"the", "and", "a", "of"}

ARTISTS = [
    "Zach Bryan", "Tyler Childers", "Sturgill Simpson", "Colter Wall", "John Prine",
    "Gillian Welch", "Jason Isbell", "Townes Van Zandt", "Johnny Cash", "Emmylou Harris",
    "MJ Lenderman", "Wednesday", "Big Thief", "Alex G", "Pavement", "Dinosaur Jr.",
    "Waxahatchee", "Wilco", "The National", "Modest Mouse", "Built to Spill",
    "Yo La Tengo", "Car Seat Headrest", "Elliott Smith", "Dutch Interior", "Sonic Youth",
    "Pixies", "Led Zeppelin", "The Rolling Stones", "Tom Petty", "Bruce Springsteen",
    "R.E.M.", "Radiohead", "Neil Young", "Fleetwood Mac", "The Cure",
    "Miles Davis", "John Coltrane", "Bill Evans", "Thelonious Monk", "Chet Baker",
    "Charles Mingus", "Duke Ellington", "Ella Fitzgerald",
    "Johann Sebastian Bach", "Antonio Vivaldi", "George Frideric Handel",
    "Ludwig van Beethoven", "Wolfgang Amadeus Mozart", "Frederic Chopin",
    "Claude Debussy", "Maurice Ravel", "Erik Satie",
    "My Bloody Valentine", "Slowdive", "Ride", "Cocteau Twins", "Whirr", "Beach House",
    "Mazzy Star", "DIIV", "Wild Nothing", "Duster",
    "American Football", "Sunny Day Real Estate", "Jawbreaker", "Cap'n Jazz",
    "The Hotelier", "Title Fight", "Jets to Brazil", "Fugazi", "The Get Up Kids",
    "Nick Drake", "Sufjan Stevens", "Jose Gonzalez", "Iron & Wine", "Phoebe Bridgers",
    "Fiona Apple", "The Smiths", "The Velvet Underground", "The Beach Boys",
    "Broken Social Scene", "The Beths", "TV Girl", "Saint Etienne", "Basement",
    "The Smashing Pumpkins", "Arctic Monkeys", "The War on Drugs", "Vampire Weekend",
]

ARTISTS += [
    "Nirvana", "Pearl Jam", "Soundgarden", "Alice in Chains", "Stone Temple Pilots",
    "Foo Fighters", "Green Day", "Red Hot Chili Peppers", "Weezer", "Oasis", "Blur",
    "Coldplay", "Muse", "The Killers", "Kings of Leon", "The White Stripes", "The Strokes",
    "Franz Ferdinand", "Jack White", "Queens of the Stone Age", "Nine Inch Nails",
    "Rage Against the Machine", "Third Eye Blind", "The Cranberries", "No Doubt",
    "Blink-182", "My Chemical Romance", "Fall Out Boy", "Paramore", "Panic! at the Disco",
    "Linkin Park", "System of a Down", "Incubus", "Hozier", "The Lumineers",
    "Mumford & Sons", "Florence + the Machine", "Tame Impala", "Arcade Fire", "Bon Iver",
    "The 1975", "Lana Del Rey", "Cage the Elephant", "Foster the People", "MGMT",
    "Portugal. The Man", "Taylor Swift", "Adele", "Ed Sheeran", "Bruno Mars", "Beyonce",
    "Rihanna", "Lady Gaga", "Katy Perry", "Justin Timberlake", "Maroon 5", "OneRepublic",
    "Sia", "Billie Eilish", "Lorde", "Harry Styles", "Sam Smith", "Dua Lipa",
    "Amy Winehouse", "John Mayer", "Alicia Keys", "Christina Aguilera", "Kelly Clarkson",
    "Pink", "Michael Jackson", "Prince", "Queen", "Whitney Houston", "Mariah Carey",
    "Kanye West", "Kendrick Lamar", "Drake", "Eminem", "Jay-Z", "Outkast", "The Weeknd",
    "Frank Ocean", "Childish Gambino", "Tyler, The Creator", "Mac Miller", "J. Cole",
    "Nas", "Lauryn Hill", "John Legend", "Usher", "D'Angelo", "SZA", "Anderson .Paak",
    "Chris Stapleton", "Kacey Musgraves", "Miranda Lambert", "Luke Combs", "Dolly Parton",
    "Willie Nelson", "Kenny Chesney", "Brad Paisley", "Stevie Wonder", "David Bowie",
    "Elton John", "Billy Joel", "Simon & Garfunkel", "Bob Dylan", "The Beatles",
]


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s.lower())).strip()


def atoken(a):
    for t in norm(a).split():
        if t not in STOP:
            return t
    return norm(a)


def key(artist, track):
    return norm(artist) + "|" + norm(track)


def base(s):
    return re.sub(r"\s*[\(\[].*", "", s).strip() or s


def itunes(term, limit=25):
    url = "https://itunes.apple.com/search?" + urllib.parse.urlencode(
        {"term": term, "entity": "song", "limit": limit, "country": "US"})
    req = urllib.request.Request(url, headers={"User-Agent": "songbird-catalog/1.0"})
    delay = 5.0
    for attempt in range(6):
        try:
            return json.load(urllib.request.urlopen(req, timeout=30)).get("results", [])
        except urllib.error.HTTPError as e:
            if e.code in (403, 429) and attempt < 5:
                time.sleep(delay)
                delay *= 2
                continue
            return []
        except Exception:
            return []
    return []


def is_live(r):
    s = norm(r.get("trackName", "") + " " + r.get("collectionName", ""))
    return any(k.strip() in s for k in LIVE_KW)


def ok(r):
    return (r.get("previewUrl")
            and r.get("primaryGenreName", "").lower() not in EXCLUDE_GENRES
            and not is_live(r))


def artist_songs(artist, n):
    res = itunes(artist, 50)
    tok = atoken(artist)
    out, seen = [], set()
    for r in res:
        if not ok(r):
            continue
        hay = norm(r.get("artistName", "") + " " + r.get("collectionName", "") + " " + r.get("trackName", ""))
        if tok not in hay:
            continue
        k = norm(r["trackName"])
        if k in seen:
            continue
        seen.add(k)
        out.append((r["trackName"], r["artistName"], r["previewUrl"], r.get("trackViewUrl", "")))
        if len(out) >= n:
            break
    return out


def library_songs():
    script = (
        'set out to ""\n'
        'tell application "Music"\n'
        '  repeat with t in (every track of library playlist 1)\n'
        '    set out to out & (name of t) & "\\t" & (artist of t) & "\\t" & (genre of t) & linefeed\n'
        '  end repeat\n'
        'end tell\n'
        'return out')
    try:
        r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=90)
    except Exception:
        return []
    songs = []
    for line in r.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 2 or not parts[0].strip():
            continue
        name, artist = parts[0].strip(), parts[1].strip()
        genre = parts[2].strip().lower() if len(parts) > 2 else ""
        if genre in EXCLUDE_GENRES:
            continue
        songs.append((name, artist))
    return songs


def load_state():
    ip = os.path.join(OUT, "index.faiss")
    if os.path.exists(ip):
        index = faiss.read_index(ip)
        rows = json.load(open(os.path.join(OUT, "index_map.json")))
        manifest = json.load(open(os.path.join(OUT, "manifest.json")))
        return index, rows, manifest
    return faiss.IndexFlatIP(1024), [], {}


def save_state(index, rows, manifest):
    os.makedirs(OUT, exist_ok=True)
    faiss.write_index(index, os.path.join(OUT, "index.faiss"))
    json.dump(rows, open(os.path.join(OUT, "index_map.json"), "w"))
    json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w"))


def main():
    reset = "--reset" in sys.argv
    max_songs = None
    for a in sys.argv[1:]:
        if a.startswith("--max="):
            max_songs = int(a.split("=")[1])
    index, rows, manifest = load_state()
    if reset:
        manifest = {k: v for k, v in manifest.items() if v == "done"}

    targets, seen = [], set()

    def add_target(t):
        kk = key(t[1], t[0])
        if kk not in seen:
            seen.add(kk); targets.append(t)

    track_files = [a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--tracks=")]
    if track_files:
        specs = []
        for tf in track_files:
            for line in open(tf, encoding="utf-8"):
                line = line.strip()
                if "|" in line:
                    a, s = line.split("|", 1)
                    specs.append((a.strip(), s.strip()))
        print("tracks to resolve:", len(specs), flush=True)
        chunk = 30
        for c0 in range(0, len(specs), chunk):
            targets.clear()
            seen.clear()
            for artist, song in specs[c0:c0 + chunk]:
                b = base(song)
                for r in itunes(f"{artist} {b}", 8):
                    if ok(r) and norm(b) in norm(r["trackName"]) and atoken(artist) in norm(r.get("artistName", "")):
                        add_target((r["trackName"], r["artistName"], r["previewUrl"], r.get("trackViewUrl", "")))
                        break
                time.sleep(4.0)
            _process(targets, index, rows, manifest, max_songs)
            print(f"batch through {min(c0 + chunk, len(specs))}/{len(specs)}", flush=True)
            time.sleep(30)
        return

    adds = [a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--add=")]
    if adds:
        for spec in adds:
            artist, song = spec.split("|", 1)
            for r in itunes(f"{artist} {song}", 8):
                if ok(r) and norm(song) in norm(r["trackName"]) and atoken(artist) in norm(r.get("artistName", "")):
                    add_target((r["trackName"], r["artistName"], r["previewUrl"], r.get("trackViewUrl", "")))
                    break
        print("targeted adds:", len(targets), flush=True)
        _process(targets, index, rows, manifest, max_songs)
        return

    print("collecting targets from", len(ARTISTS), "artists...", flush=True)
    for a in ARTISTS:
        for t in artist_songs(a, SONGS_PER_ARTIST):
            add_target(t)
        time.sleep(0.2)
    lib = library_songs()
    print("library songs:", len(lib), flush=True)
    for name, artist in lib:
        res = itunes(f"{artist} {name}", 5)
        time.sleep(0.15)
        for r in res:
            if ok(r) and norm(name) in norm(r["trackName"]):
                add_target((r["trackName"], r["artistName"], r["previewUrl"], r.get("trackViewUrl", "")))
                break
    print("total unique targets:", len(targets), flush=True)
    _process(targets, index, rows, manifest, max_songs)


def _process(targets, index, rows, manifest, max_songs):
    n = 0
    for track, artist, url, apple in targets:
        kk = key(artist, track)
        if kk in manifest:
            continue
        if max_songs is not None and sum(1 for v in manifest.values() if v == "done") >= max_songs:
            break
        try:
            m = embed_all(load(url))
            index.add(np.ascontiguousarray(m, dtype=np.float32))
            rows.extend([[track, artist, apple] for _ in range(len(m))])
            manifest[kk] = "done"
        except Exception as e:
            manifest[kk] = "skip:" + repr(e)[:40]
        n += 1
        if n % CHECKPOINT_EVERY == 0:
            save_state(index, rows, manifest)
            done = sum(1 for v in manifest.values() if v == "done")
            print(f"checkpoint: {done} songs, {index.ntotal} vectors", flush=True)

    save_state(index, rows, manifest)
    done = sum(1 for v in manifest.values() if v == "done")
    skipped = sum(1 for v in manifest.values() if v != "done")
    print(f"DONE: {done} songs, {index.ntotal} vectors, {skipped} skipped -> {OUT}")


if __name__ == "__main__":
    main()

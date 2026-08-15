# Songbird

Link a **live recording** of a song to its **studio original**. Songbird returns
the song's name, artist, and where to hear the studio version (Apple Music,
Spotify). It recognizes song *identity* across tempo, key, arrangement, and
performance changes — not an acoustic fingerprint (Shazam), not a video ID.

## How it works

```
audio / video file or YouTube URL
  → librosa 24 kHz mono (video → ffmpeg audio extract first)
  → 10s windows, 5s hop (20s option)
  → MuQ embedding on CPU → mean-pool over time → L2-normalize
  → FAISS IndexFlatIP (cosine)
  → per-window top-k, temperature-weighted vote
  → aggregate across windows → argmax → song identity
  → Apple Music + Spotify search links
```

Method follows the *tipofmyear* paper (Eser, ICML 2026 workshop) findings:
frozen pretrained embeddings + kNN retrieval + performance-level aggregation.

## Setup

```
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Requires `ffmpeg` and the VLC desktop app (libVLC) installed (the streamer uses
them). MuQ (`OpenMuQ/MuQ-large-msd-iter`, CC-BY-NC 4.0) downloads on first use
and runs on CPU — correct but slow.

## Build the reference index

Drop studio tracks into `reference/` and list them in `reference/metadata.csv`:

```
filename,song,artist
so_what.mp3,So What,Miles Davis
```

Then:

```
.venv/bin/python build_reference.py
```

This writes `data/index.faiss` and `data/index_map.json`. Adding a song later is
just another row + rebuild — no retraining.

## Match

Desktop streamer (upload a file or match a loaded YouTube link):

```
.venv/bin/python songbird/streamer/link-stream.py
```

Headless:

```
.venv/bin/python -c "from songbird.matcher import match; print(match('live.mp3'))"
```

## Self-checks

Each module has an assert-based check:

```
.venv/bin/python -m songbird.audio
.venv/bin/python -m songbird.embed
.venv/bin/python -m songbird.windowing
.venv/bin/python -m songbird.index
.venv/bin/python -m songbird.matcher
.venv/bin/python -m songbird.links
```

## Notes

- Reference corpus is user-supplied; the index is empty until you add songs.
- Accuracy tracks the paper's Top-5 behavior (right song in the neighborhood;
  aggregation pushes it toward rank 1). This is a hard problem — expect misses.
- A supervised contrastive projection (paper §6) is available to add only if
  wrong-song-same-artist confusion appears.

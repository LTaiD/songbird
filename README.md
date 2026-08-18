# Songbird

Songbird finds the studio original of a live recording. Give it an audio file, a
video file, or a YouTube link. Songbird tells you the song name and the artist.
It also gives you links to the studio version on Apple Music and Spotify.

Songbird finds the same song when the tempo, the key, the arrangement, or the
performance changes. It compares the musical identity of the song.

## How it works

```
audio or video file, or YouTube URL
  → librosa reads the audio at 24 kHz, mono (ffmpeg extracts audio from video first)
  → split into 10 second windows, 5 second hop (20 second option)
  → MuQ makes an embedding on the CPU → mean-pool over time → L2-normalize
  → FAISS IndexFlatIP (cosine)
  → top-k per window, temperature-weighted vote
  → add the votes across windows → argmax → song identity
  → Apple Music and Spotify search links
```

This method follows the tipofmyear paper (Eser, ICML 2026 workshop). The paper
uses frozen pretrained embeddings, kNN retrieval, and performance-level
aggregation.

## Setup

```
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Install ffmpeg first. The streamer needs ffmpeg and the VLC application
(libVLC). Songbird downloads MuQ (`OpenMuQ/MuQ-large-msd-iter`, CC-BY-NC 4.0) on
first use. MuQ runs on the CPU. The CPU path is slow.

## Build the reference index

Put your studio tracks in `reference/`. List them in `reference/metadata.csv`:

```
filename,song,artist
so_what.mp3,So What,Miles Davis
```

Then run:

```
.venv/bin/python build_reference.py
```

This writes `data/index.faiss` and `data/index_map.json`. To add a song later,
add a row and build the index again. You do not need to train the model again.

## Match

Run the streamer. Upload a file, or load a YouTube or TikTok link and match it:

```
.venv/bin/python songbird/streamer/link-stream.py
```

Songbird runs the identification in a separate worker process
(`songbird/streamer/identify_worker.py`). A native crash in the worker does not
stop the streamer. The streamer resolves a loaded link again at match time. A
simple fallback streamer is `songbird/streamer/prototypes/shell.py`.

Run without the streamer:

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

- You supply the reference songs. The index stays empty until you add songs.
- Accuracy follows the Top-5 behavior in the paper. The correct song is usually
  in the neighborhood, and aggregation moves it toward rank 1. This is a hard
  problem. Expect some misses.
- A supervised contrastive projection (paper section 6) is available. Add it only
  if you see wrong-song-same-artist confusion.

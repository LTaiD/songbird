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

Frozen pretrained embeddings, kNN retrieval, and performance-level
aggregation.

## Setup

```
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Install ffmpeg first. Songbird downloads MuQ (`OpenMuQ/MuQ-large-msd-iter`,
CC-BY-NC 4.0) on first use. MuQ runs on the CPU. The CPU path is slow.

For URL identification (YouTube, TikTok, SoundCloud), yt-dlp needs the `curl_cffi`
impersonation backend (in `requirements.txt`) and a current build. TikTok and
YouTube change often, so use the nightly:

```
.venv/bin/pip install -U --pre "yt-dlp[default]"
```

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

Songbird runs as a localhost web app. Paste a URL or drop an audio/video file;
it returns one song with Apple Music, Spotify, and TikTok links.

Backend (FastAPI), from the repo root:

```
.venv/bin/uvicorn server.app:app --port 8000
```

Frontend, in another terminal:

```
cd web && npm install && npm run dev
```

Open the Vite URL (http://localhost:5173). For a single-process setup, build the
frontend (`cd web && npm run build`) and open http://localhost:8000 — the backend
serves `web/dist`.

The endpoint is also usable directly:

```
curl -F url='https://www.youtube.com/watch?v=...' localhost:8000/identify
curl -F file=@live.mp3 localhost:8000/identify
```

Run without the web layer:

```
.venv/bin/python -c "from songbird.matcher import match; print(match('live.mp3'))"
```

The old PySide6 desktop streamer lives outside this repo at
`../songbird-streamer-gui`.

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

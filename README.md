# Songbird

![Songbird](assets/screenshot.png)

Songbird finds the studio original of a live recording. You give it an audio file, a video file, or a link. It tells you the song and the artist. It links the studio version on Apple Music, Spotify, and TikTok.

It works when the tempo, key, arrangement, or performance changes. It even works on a cover by a different band. It matches on musical identity, the way the song actually goes.

## How it works

```
audio or video file, or a URL
  -> ffmpeg pulls the audio, librosa reads it at 24 kHz mono
  -> trim to the music (drop spoken intros and silence)
  -> split into 10s windows, 5s hop
  -> MuQ embeds each window on CPU, mean-pool over time, L2-normalize
  -> FAISS IndexFlatIP (cosine), per-window top-k, temperature-weighted vote
  -> keep the most confident ~1/3 of windows, sum votes, build a recall set
  -> chroma chord-progression rerank, fused with the catalog chroma store
  -> single argmax, then song, artist, Apple URL
  -> Apple Music, Spotify, and TikTok links
```
**MuQ timbre retrieval.** Frozen pretrained embeddings with kNN. Recall is strong. The right song is almost always in the top few. But top-1 gets shaky at scale, and it can land on a song that just sounds similar.

**Chroma chord-progression rerank.** HPSS harmonic separation, CENS, and transposition-invariant local alignment. It survives distortion and instrument changes. It knows the song across a totally different band. This is what pushes the correct song past a look-alike.

Frozen embeddings plus kNN retrieval.

## Setup

```
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Install ffmpeg first with `brew install ffmpeg`. Songbird downloads MuQ on first use. That model is `OpenMuQ/MuQ-large-msd-iter`, licensed CC-BY-NC 4.0, so this is a non-commercial build. MuQ runs on CPU. It is slow but it works.

For link identification, yt-dlp needs the `curl_cffi` backend and a current build. TikTok and YouTube change often, so use the nightly.

```
.venv/bin/pip install -U --pre "yt-dlp[default]"
```

One catch with YouTube. Some videos now need a PO token and will 403 on download. TikTok, SoundCloud, direct media, and file uploads all work.

## The reference catalog

Songbird matches against a catalog of studio tracks. The matcher defaults to `data/catalog`. Each row holds the song, the artist, and an Apple URL.

`data/` is gitignored, so a fresh clone has no catalog. You build one before the app can identify anything. The catalog comes from copyrighted Apple Music and iTunes content, so I don't ship it here. Mine has about 3,600 songs from Apple Music editorial playlists.

Build the catalog.

```
.venv/bin/python build_catalog.py --tracks path/to/tracks.txt
.venv/bin/python build_chroma.py
```

`build_catalog.py` resolves each track through the iTunes Search API and embeds the 30-second preview. `build_chroma.py` finds new songs from `index_map.json` on its own. Both resume from a manifest, so you can re-run them. Watch progress with `scripts/progress.py`.

The iTunes API bans your IP after a burst. The builders pace requests and back off. If you get banned, wait 15 to 30 minutes.

### Bring your own reference songs

For a small hand-picked set, drop studio files in `reference/` and list them in `reference/metadata.csv`.

```
filename,song,artist
so_what.mp3,So What,Miles Davis
```

Then build a small index.

```
.venv/bin/python build_reference.py
```

Pass `data_dir="data"` to `match()` to use it.

## Run it

Songbird runs as a localhost web app. Paste a link or drop a file. You get one result card with Apple Music, Spotify, and TikTok links.

Start the backend from the repo root.

```
.venv/bin/uvicorn server.app:app --port 8000
```

Start the frontend in another terminal.

```
cd web && npm install && npm run dev
```

Open the Vite URL at http://localhost:5173. For one process, build the frontend and let the backend serve it.

```
cd web && npm run build
```

Then open http://localhost:8000.

### The API

POST to `/identify` with multipart form data. A `url` field wins over a `file` field.

```
curl -F url='https://www.tiktok.com/@user/video/...' localhost:8000/identify
curl -F file=@live.mp3 localhost:8000/identify
```

It returns five fields.

```json
{"song": "...", "artist": "...", "apple": "...", "spotify": "...", "tiktok": "..."}
```

A null result returns 422. A fetch or decode error returns 400. The server caps queries at 90 seconds and uses `recall_k=12`.

### Without the web layer

```
.venv/bin/python -c "from songbird.matcher import match; print(match('live.mp3'))"
```

## Deploy

The frontend and backend deploy in different places. The backend is a heavy, stateful ML service, so it does not fit serverless.

The frontend goes on Vercel. Config lives in `web/vercel.json` with root directory `web`. Set `VITE_API_BASE` to your backend URL. That value is public. It ships in the browser bundle, so it must never hold a secret. See `web/.env.example`.

The backend goes on Modal. See `deploy/modal_app.py`. There is no Dockerfile. Modal builds the image in Python. The MuQ model bakes into the image. The catalog lives on a Modal volume.

```
pip install modal
modal token new
modal volume create songbird-catalog
modal volume put songbird-catalog ./data/catalog /
modal deploy deploy/modal_app.py
```

Set `VITE_API_BASE` on Vercel to the printed Modal URL and redeploy the frontend. The backend reads two env vars from `modal_app.py`. `SONGBIRD_CATALOG` sets the catalog path. `SONGBIRD_ALLOWED_ORIGINS` sets the CORS allow-list. Both default to local values, so local runs stay the same.

## Project layout

```
songbird/            core pipeline (importable, no side effects beyond MuQ load)
  audio.py           load / decode to 24 kHz mono (ffmpeg for video and URLs)
  activity.py        music-activity detection and trim (RMS, HPSS, chroma peakiness)
  windowing.py       10s / 5s windows
  embed.py           MuQ per-window embedding, mean-pool, L2-norm
  index.py           FAISS load, OpenMP thread cap (see note below)
  matcher.py         windowed vote and gated chroma-fusion, single answer
  rerank.py          chroma_cens / OTI / local alignment scoring
  chroma_index.py    precomputed chroma store and gated fuse()
  links.py           Apple / Spotify / TikTok search URLs
  projection.py      SupCon projection (NOT wired in, see Notes)
server/app.py        FastAPI /identify, serves web/dist, CORS for :5173
web/                 Vite + React 19 + TS + Tailwind v4 frontend
build_catalog.py     build or extend the studio embedding catalog (iTunes)
build_chroma.py      build or extend the chroma fingerprint store
build_reference.py   build a small index from reference/metadata.csv
scripts/             add_songs, bench_identify, fetch_playlists, progress
data/catalog/        prebuilt catalog, index.faiss, index_map.json, chroma.pkl
specs/               Spec Kit specs (001-songbird ... 004-web-frontend)
```

## Self-checks

Each core module has an assert-based check.

```
.venv/bin/python -m songbird.audio
.venv/bin/python -m songbird.embed
.venv/bin/python -m songbird.windowing
.venv/bin/python -m songbird.index
.venv/bin/python -m songbird.matcher
.venv/bin/python -m songbird.chroma_index
.venv/bin/python -m songbird.links
```

Run the backend contract tests from the repo root.

```
.venv/bin/python -m pytest
```

Use `-m pytest`, not bare `pytest`. The test imports `server.app` with no sys.path setup at collection time.

Run the end-to-end benchmark on the known queries.

```
.venv/bin/python scripts/bench_identify.py
```

## Notes

**One answer, always.** Exactly one song and its links. No shortlist.

**Accuracy tracks the paper's top-1 vs top-5 gap.** The right song is almost always nearby. Aggregation and the chroma rerank push it toward rank 1. Hard live and cover queries can still return a look-alike. This is a hard problem. Expect some misses.

**The OpenMP clash is load-bearing on macOS arm.** torch and faiss-cpu each ship their own libomp. `songbird/__init__.py` sets `KMP_DUPLICATE_LIB_OK=TRUE`. `songbird/index.py` caps faiss to one thread. In any ad-hoc script, import a songbird module before you import faiss, or the MuQ forward pass segfaults.

**The projection is not used.** I tested `songbird/projection.py` and it made open-set retrieval worse at small scale. It overfits and warps unseen songs. Raw MuQ has the right ordering. `data/projection.pt` exists but nothing wires it in. Revisit it only with hundreds or thousands of training songs.

## Security and going public

The `/identify` endpoint ships with basic guards.

**Rate limit.** Per-IP fixed window. `SONGBIRD_RATE_LIMIT` requests per `SONGBIRD_RATE_WINDOW` seconds, default 10 per 60. Over that returns 429. It is in-memory per container. The client IP comes from `X-Forwarded-For`.

**Upload cap.** 30 MB. Over that returns 413.

**SSRF guard.** See `_check_public_url`. A URL must be http or https. It must not resolve to a private, loopback, or link-local range. The check runs before any fetch.

**CORS.** Driven by `SONGBIRD_ALLOWED_ORIGINS`. It defaults to localhost. Set it to your frontend domain in production. Never use a wildcard.

On Modal, `max_containers` bounds the cost if someone floods it.

The rate limit is per container, not global. The SSRF guard checks the user's URL but not every redirect yt-dlp follows. That is fine at this scale. Add a shared store like Redis, or auth, if traffic grows. I keep no secrets in this repo. Keep it that way.

## Licensing

The code is MIT. See `LICENSE`.

MuQ (`OpenMuQ/MuQ-large-msd-iter`) is CC-BY-NC 4.0. That makes this a research and demo build, not a commercial one.

The catalog and reference audio come from copyrighted Apple Music and iTunes content. They're not in the repo, you build your own. But on the website you don't need to.

## Method

The method follows the tip-of-my-ear paper by Eser, from the ICML 2026 workshop. I used the findings only. I imported no paper code.

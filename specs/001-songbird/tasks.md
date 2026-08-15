# Tasks: Songbird

Aligned to build spec §8. Each code task ends with a runnable self-check.

## Phase 1 — Environment
- [ ] T001 Fresh `.venv` (py3.13); install torch-cpu, muq, librosa, faiss-cpu, numpy<2, + streamer requirements. Combined root `requirements.txt`.

## Phase 2 — Core pipeline
- [ ] T002 `songbird/audio.py` — `load(path)`→24kHz mono; video→ffmpeg extract first. Self-check: sr=24000, 1-D.
- [ ] T003 `songbird/embed.py` — singleton MuQ CPU; `embed_window(wav)`→ meanpool+L2 `(D,)`. Self-check: 1-D, unit norm.
- [ ] T004 `songbird/windowing.py` — `windows()` 10s/5s (+20s), `embed_all()`→`(N,D)`. Self-check: window count.

## Phase 3 — Reference index
- [ ] T005 `songbird/index.py` — `build/save/load` IndexFlatIP + (song,artist) rows. Self-check: save→load round-trip.
- [ ] T006 `build_reference.py` — ingest `reference/` + metadata.csv → `data/`. Self-check: writes artifacts.

## Phase 4 — Matcher
- [ ] T007 `songbird/matcher.py` — top-k vote + aggregate + argmax. Self-check: synthetic index returns planted song; empty index handled.

## Phase 5 — Links
- [ ] T008 `songbird/links.py` — Apple + Spotify search URLs, url-encoded. Self-check: encoding + well-formed.

## Phase 6 — Streamer integration
- [ ] T009 Copy streamer → `songbird/streamer/`; add Match-file button + QFileDialog; match loaded YouTube audio; QThread worker; show only 4 fields.

## Phase 7 — Verify end-to-end
- [ ] T010 Run all self-checks; build tiny index; headless matcher smoke; launch streamer; confirm 4-field output = song identity.

## Deferred
- [ ] T011 Supervised contrastive projection — only if same-artist confusion appears.

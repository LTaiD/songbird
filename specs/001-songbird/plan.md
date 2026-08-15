# Implementation Plan: Songbird

**Spec**: `./spec.md` · **Constitution**: `../../.specify/memory/constitution.md`

## Technical context

- **Language/runtime**: Python 3.13 in a fresh repo `.venv` (fall back to 3.11 if any wheel is missing).
- **Embedding**: MuQ `OpenMuQ/MuQ-large-msd-iter` via the `muq` pip package (`from muq import MuQ`), `device="cpu"`, frozen.
- **Audio**: librosa (24 kHz mono); ffmpeg for video audio extraction.
- **Vector search**: `faiss-cpu`, `IndexFlatIP` (cosine via inner product on L2-normalized vectors).
- **UI**: PySide6 desktop streamer copied from `../songbird-archive-streamer` (libVLC + yt-dlp), edited copy only.
- **numpy<2** pinned (librosa/torch compat).

## Architecture

```
file / YouTube URL
  → librosa 24kHz mono (video → ffmpeg first)
  → windowing (10s win, 5s hop; 20s option)
  → MuQ per window (CPU) → mean-pool over time → L2-normalize
  → FAISS IndexFlatIP → per-window top-k
  → temperature-weighted vote (exp(sim/tau)) → sum across windows → argmax
  → link resolver (Apple + Spotify search URLs)
  → return: song name, artist, Apple Music link, Spotify link
```

## Math (implement exactly)

- Window embedding: `v = mean(H, axis=time)`, `v_hat = v/‖v‖₂`, shape `(D,)`. Every ref and query vector L2-normalized before FAISS.
- Voting: `weight(row)=exp(sim_row/tau)`, `score_window(c)=Σ weight over retrieved rows whose song is c`, `tau∈[0.05,0.2]`.
- Aggregate: `score_perf(c)=Σ_windows score_window(c)`, `prediction=argmax_c score_perf(c)`.
- Deferred: supervised contrastive projection (`L=L_CE+0.2·L_SupCon`, positives = same-song-different-performance) only if same-artist confusion appears.

## Module layout

- `songbird/audio.py`, `songbird/embed.py`, `songbird/windowing.py`, `songbird/index.py`, `songbird/matcher.py`, `songbird/links.py`
- `build_reference.py` (root) — ingest studio audio + `reference/metadata.csv` → `data/index.faiss` + `data/index_map.json`
- `songbird/streamer/` — edited copy of the streamer
- Each non-trivial module ships one `assert`-based `__main__` self-check.

## Project structure decisions

- Streamer stays a subpackage; matcher package is flat under `songbird/`.
- Reference artifacts live in `data/`; user audio in `reference/` (gitignored large media).

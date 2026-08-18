# Implementation Plan: Flying-bird header + crash-proof, faster identification

**Branch**: `003-bird-fast-identify` | **Date**: 2026-08-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/003-bird-fast-identify/spec.md`

## Summary

Three slices on the promoted Blue-Note streamer UI:
1. **Crash-proof Identify (P1)** — move matching out of the Qt process into a long-lived worker
   process driven via `QProcess`; a native segfault can no longer take down the GUI. Fix the loaded-
   link HTTP 403 by returning the original page URL from the engine and re-resolving fresh audio in
   the worker at match time.
2. **Faster Identify (P2)** — batch the MuQ forward passes (one padded batch instead of ~47
   sequential CPU calls) and add two configs to `matcher.match` (a capped ~90 s slice with a smaller
   rerank fan-out, and a full-track pass), then benchmark both blind on the 3 provided songs.
3. **Flying-bird header (P3)** — render the header square field as a wings-spread bird via a
   `QPainterPath` fill test, dissolving into the existing seeded sparse scatter.

## Technical Context

**Language/Version**: Python 3.13 (repo `.venv`)

**Primary Dependencies**: PySide6 (Qt) GUI, python-vlc, yt-dlp, MuQ (torch), faiss, librosa, numpy

**Storage**: FAISS flat index + JSON map under `data/catalog/` (1102 songs); reference audio in `reference/`

**Testing**: per-module `_demo()` assert self-checks (`python -m songbird.<mod>`); benchmark script

**Target Platform**: macOS desktop (darwin), CPU-only

**Project Type**: Desktop app (Qt) + Python library pipeline

**Performance Goals**: identify a ~4-min recording ≥ ~3× faster than the sequential baseline

**Constraints**: CPU-only MuQ; GUI must never crash from matching; output contract = song/artist/links

**Scale/Scope**: single-user desktop; catalog ~1k songs; 3-song benchmark

## Constitution Check

*GATE: re-checked after Phase 1 design — PASS with noted items.*

- **P1 No code comments** — new files (`identify_worker.py`, `bench_identify.py`) and new code will be
  comment-free. NOTE: the existing streamer/pipeline files are already heavily commented (pre-existing
  repo state); edits there match surrounding style. No net new comment debt introduced by new modules.
- **P2 No agent VCS** — no commits/branches by the agent; user owns VCS. ✓
- **P3 FAISS only** — unchanged; still `IndexFlatIP`. ✓
- **P4 MuQ on CPU** — worker loads MuQ on CPU; only sets CPU thread count. ✓
- **P5 `songbird-archive-streamer` untouchable** — that path does not exist here; work is in `songbird/streamer`. ✓
- **P8 Output contract** — user-facing identify returns song/artist/links only. Benchmark top-k/scores
  are internal (never shown in the app UI), consistent with the contract. (Existing UI also shows a
  TikTok link — pre-existing, unchanged.)
- **P9 Performance-level aggregation** — both configs aggregate across many windows; the **full**
  config uses all windows (strictly compliant). The **cap** config aggregates across all windows of a
  ~90 s span (never a single window) and is a benchmarked variant; default to the compliant/best per
  the benchmark. ✓

No unjustified violations → gate passes.

## Project Structure

### Documentation (this feature)

```text
specs/003-bird-fast-identify/
├── plan.md            # this file
├── research.md        # Phase 0
├── data-model.md      # Phase 1
├── quickstart.md      # Phase 1
├── contracts/
│   └── worker-protocol.md   # GUI <-> identify worker JSON line protocol
└── tasks.md           # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
songbird/
├── embed.py            # + batched embed_windows()
├── windowing.py        # embed_all() uses the batch path
├── matcher.py          # match(..., max_seconds, recall_k) for the two configs
└── streamer/
    ├── engine.py           # match_source() returns the page URL (403 fix)
    ├── link-stream.py      # flying-bird HeaderBand; QProcess identify client
    ├── identify_worker.py  # NEW: warm MuQ+faiss worker, fresh URL resolve
    └── prototypes/shell.py # fallback UI must keep working (unchanged)

scripts/
└── bench_identify.py   # NEW: blind cap-vs-full speed/accuracy benchmark

reference/              # add Congress – Out the Door studio ref before benchmarking
```

**Structure Decision**: Existing single-repo layout; the streamer talks to the pipeline via a new
process boundary (`identify_worker.py`). No new top-level projects.

## Complexity Tracking

No unjustified constitution violations; table omitted.

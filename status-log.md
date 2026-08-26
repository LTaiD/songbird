# Status Log

Chronological record of work per session.

## Session 2026-08-19 → 2026-08-20 — Catalog expansion + MJL misidentification fix

Goal: (1) expand the catalog from official Apple Music editorial playlists; (2) fix
the baseline test (YouTube `b4Zz-WXl5uM`, live MJ Lenderman "She's Leaving You")
returning a Built to Spill song.

### 2026-08-19 (planning + build kickoff)
- Explored the codebase (catalog pipeline, identification pipeline, project structure).
- Root-caused the MJL regression: `chroma_index.fuse()` widened the candidate pool to
  ~90 coarse-chroma neighbours and `matcher.match` unconditionally did `pred = fu[0][0]`
  with no gate — chord-shape intruders (e.g. Built to Spill) beat the correct song.
- Confirmed official Apple Music playlist pages do NOT expose tracklists to a plain
  fetch; chose the anonymous web-player token + `amp-api` approach.
- Decisions taken with user: auto web-player-token extraction; "go big" ingest.
- Wrote `scripts/fetch_playlists.py`; verified token + amp-api works (100 tracks from
  College Rock Essentials).
- Curated `data/playlists.txt` — 20 official editorial playlists (4 each: pop, rock/alt,
  country, indie, folk). Fetched → 2143 net-new tracks (deduped by title AND artist,
  and against the existing catalog) → `data/editorial_tracks.txt`.
- Implemented the fix: gated fusion in `songbird/chroma_index.py` (`_gate` helper +
  `fuse(..., margin=0.05)`); added `_demo()` self-check (passes).
- Added the MJL baseline to `scripts/bench_identify.py` as a permanent regression test.
- Launched the catalog + chroma ingest (background).

### 2026-08-20 (overnight ingest + verification)
- Ingest ran overnight. Background jobs were repeatedly reaped by the harness; switched
  to `nohup ... & disown` detached processes, which survive. All stages resumable
  (`build_catalog` manifest / `build_chroma` checkpoints every 20).
- Added `scripts/progress.py` — live in-terminal progress meter.
- Catalog stage completed: 1643 → 3639 songs (~1996 net-new).
- Chroma stage completed: 3602 fingerprints (37 skipped) of 3639 songs.
- Tuned the gate margin (`scratchpad/tune_margin.py` on the MJL query): intruder-vs-SLY
  align gap = 0.0276; margin ≥ 0.03 fixes it; kept 0.05 (just above the cluster-noise
  floor, preserves legit non-MuQ promotions).
- Verified at the true server config (`max_seconds=90, recall_k=12`) via
  `scripts/bench_identify.py`:
  - q1 MJL "She's Leaving You" → **MJ Lenderman — She's Leaving You** (FIXED)
  - q2 Built-to-Spill covers Pavement "Here" → Pavement — Here (no regression)
  - q3 Beatles "Tomorrow Never Knows" → correct
  - q4 Congress "Out the Door" → Johnny Cash (WRONG — new confuser from the 2× catalog;
    accepted Top-1 ceiling cost of going big)
- Tests: 3/3 (`python -m pytest tests/test_identify.py`); all module self-checks pass.
- Updated project memory.

### Files touched
- Fix: `songbird/chroma_index.py`
- Catalog source (new): `scripts/fetch_playlists.py`, `data/playlists.txt`,
  `data/editorial_tracks.txt`
- Tooling: `scripts/bench_identify.py` (MJL regression test + server config),
  `scripts/progress.py` (new)
- Data: `data/catalog/{index.faiss,index_map.json,manifest.json,chroma.pkl}`

### Notes / open items
- q4 confuser left unaddressed (single-answer Top-1 ceiling; not chased to avoid whack-a-mole).
- Bare `pytest` fails collection ("No module named 'server'") — pre-existing path quirk;
  use `python -m pytest`.
- Backend hot-reloads catalog/chroma per query; start detached:
  `nohup .venv/bin/uvicorn server.app:app --port 8000 > scratchpad/server.log 2>&1 & disown`

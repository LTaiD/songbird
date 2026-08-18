# Quickstart / Validation

Prereqs: repo `.venv` populated, `ffmpeg` + VLC installed, `data/catalog/` present.

## 1. Module self-checks (batched embedding equivalence)

```bash
.venv/bin/python -m songbird.embed
.venv/bin/python -m songbird.windowing
.venv/bin/python -m songbird.matcher
```

Expected: each prints `ok`. The embed/windowing checks assert batched embeddings match the per-window
result (accuracy unchanged).

## 2. Run the app — header + crash-proof identify

```bash
.venv/bin/python songbird/streamer/link-stream.py
```

- Header shows a wings-spread bird made of squares dissolving into the sparse field.
- **File upload** an audio file → **Identify Song** → result panel shows song/artist + links; window
  stays responsive.
- Paste a link → **Load** → **Identify Song** → no HTTP 403; result appears.
- While an identify runs, kill the worker process (e.g. `pkill -f identify_worker`) → GUI reports a
  failure and stays alive; a second Identify still works (worker respawns).

## 3. Fallback UI still works

```bash
.venv/bin/python songbird/streamer/prototypes/shell.py
```

## 4. Benchmark (needs the two external inputs first)

Add Congress – "Out the Door" studio audio to `reference/` (+ metadata row), rebuild, then:

```bash
.venv/bin/python build_reference.py      # or build_catalog.py, per how the ref was added
.venv/bin/python scripts/bench_identify.py
```

Expected: a table of `cap` vs `full` for the 3 songs — elapsed seconds, prediction, correct? — plus
per-config accuracy % and mean/median latency. Temp query files are neutrally named (no title), and no
title/artist is passed to the identifier (blind).

## Pass criteria (maps to Success Criteria)

- No app crash across identify runs, including worker-kill (SC-001).
- Loaded-link identify has no 403 (SC-002).
- Benchmark shows a large speedup vs the sequential baseline (SC-003) and reports both configs (SC-004).
- Neutral filenames + no title passed (SC-005). Header reads as a flying bird (SC-006). Shell UI runs (SC-007).

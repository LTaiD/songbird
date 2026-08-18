# Tasks: Flying-bird header + crash-proof, faster identification

**Feature**: `003-bird-fast-identify` | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Constitution note: new files must contain **no code comments**. Verification uses the repo's existing
`_demo()` self-checks (no new test framework).

## Phase 1: Setup

- [X] T001 Confirm `.venv` runs and the catalog loads (catalog has 1102 songs, verified).

## Phase 2: Foundational (shared prerequisites)

- [X] T002 [P] Added batched `embed_windows(wavs, batch_size=8)` in `songbird/embed.py` (chunked `(B, win)` MuQ forward, per-row mean-pool + L2-norm).
- [X] T003 `songbird/windowing.py` `embed_all()` now uses `embed_windows`; equivalence asserted in `embed._demo()` (batched == per-window, verified).
- [X] T004 Added `max_seconds=None` to `songbird/matcher.py` `match()` (slices trimmed wav to `max_seconds*SR`); `recall_k` already a param.

## Phase 3: User Story 1 — Crash-proof Identify + 403 fix (P1) 🎯 MVP

**Goal**: Identification can't crash the GUI, and loaded links no longer 403.
**Independent test**: Load a link → Identify → result, no 403; kill the worker mid-run → GUI survives and re-identifies.

- [X] T005 [US1] `engine.py` stores `self._page_url` in `load()`; `match_source()` returns the page URL.
- [X] T006 [US1] Created `songbird/streamer/identify_worker.py` (warm model, `is_url` fresh yt-dlp resolve, newline-JSON per contract). Validated end-to-end on a local file — clean JSON, no segfault in the isolated process.
- [X] T007 [US1] `link-stream.py` now uses a `QProcess` client (`_ensure_worker`, `_on_worker_out`) instead of a daemon thread.
- [X] T008 [US1] Crash handling (`_on_worker_finished` → failure + respawn) and a 180 s `QTimer` watchdog (`_on_match_timeout`) added; worker killed in `closeEvent`.
- [X] T009 [US1] `match_file` (is_url=false) and `match_loaded` (is_url=true) route through the client; Identify buttons disabled while matching.
- [~] T010 [US1] `py_compile` + offscreen Window build pass; worker validated on a file. **Pending manual GUI run**: live link (no 403) + `pkill -f identify_worker` crash-survival.

## Phase 4: User Story 2 — Faster Identify + benchmark (P2)

**Goal**: Identification is materially faster; two configs benchmarked blind on 3 songs.
**Independent test**: Run the benchmark → table of cap vs full latency + accuracy on the 3 songs.

- [X] T011 [US2] Configs defined in `identify_worker.py` and `bench_identify.py` (cap = 90 s/recall_k 5, full = none/12); worker sets `torch.set_num_threads(cpu_count)`.
- [X] T012 [US2] Created `scripts/bench_identify.py` (neutral `q{n}` temp files, both configs, per-song table + per-config accuracy % and mean/median latency).
- [X] T013 [US2] Blind guardrail: no title passed to `match`; filename `q{n}` asserted metadata-free.
- [ ] T014 [US2] **GATED** — add "Congress the Band – Out the Door" studio reference + rebuild catalog; needs user-provided audio + ground-truth map for the 3 URLs.
- [ ] T015 [US2] **GATED** — self-checks done (embed/windowing/matcher pass); benchmark run awaits T014.

## Phase 5: User Story 3 — Flying-bird header (P3)

**Goal**: Header squares form a wings-spread flying bird dissolving into the scatter.
**Independent test**: Launch the app; header reads as a flying bird.

- [X] T016 [US3] Reworked `HeaderBand` (`_bird_path` + `_squares`): a flying-bird `QPainterPath` (swept-wing gull), filled navy squares inside it dissolving into the seeded scatter trail; `HEADER_HEIGHT` raised to 158 for detail. Verified via offscreen PNG render.
- [~] T017 [US3] Verified via offscreen render (reads as a flying bird). **Pending live app** visual confirm of full-window layout.

## Phase 6: Polish & Cross-Cutting

- [X] T018 [P] Fallback UI `shell.py` builds/launches (offscreen build verified).
- [X] T019 [P] `README.md` match section notes the worker isolation + fresh re-resolve; run command unchanged.
- [X] T020 Final `py_compile` across all touched files passes; embed/windowing/matcher self-checks pass.

## Dependencies & order

- Phase 2 (T002–T004) blocks US2 (batching + `max_seconds`) and is used by the worker in US1.
- **US1 (P1)** is the MVP and can ship after Phase 2 + T005–T010.
- **US2 (P2)** depends on Phase 2 and the worker (T006); T014–T015 are **gated** on user-provided inputs (Congress audio + ground-truth).
- **US3 (P3)** is independent (paint-only) and can be done any time.

## Parallel opportunities

- T002 (embed) ∥ T005 (engine) — different files.
- T016 (header) is independent of all identify work.
- T018/T019 polish can run in parallel.

## MVP scope

**User Story 1** (crash-proof + 403 fix) after Phase 2 — restores the core feature without crashing.
US3 (header) is a cheap independent add. US2's benchmark (T014–T015) waits on the two external inputs.

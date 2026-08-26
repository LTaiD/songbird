---
description: "Task list for Localhost Web Frontend"
---

# Tasks: Localhost Web Frontend

**Input**: Design documents from `/specs/004-web-frontend/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/identify.md, quickstart.md

**Tests**: One backend smoke test requested (quickstart automated check). No frontend unit tests.

**Organization**: Grouped by user story. US1 (URL identify) is the MVP; US2 (file identify) extends it.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on incomplete tasks)
- Constraints (all tasks): NO code comments; NO git commits; core `songbird/` UNCHANGED.

---

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Relocate the old GUI out of the repo: `mv songbird/streamer ~/VSCodeProjects/songbird-streamer-gui` (do NOT touch `../songbird-archive-streamer`). Confirm nothing under `songbird/*.py` imports `streamer`.
- [X] T002 Edit root `requirements.txt`: remove `python-vlc` and `PySide6`; add `fastapi`, `uvicorn[standard]`, `python-multipart`. Install into the existing `.venv`.
- [X] T003 Scaffold the frontend: `npm create vite@latest web -- --template react-ts`, then add Tailwind CSS v4, `thinking-orbs`, and `sonner` in `web/`. Load design tooling into the agent: `npx skills add Leonxlnx/taste-skill` and apply the local `/better-ui`, `/better-colors`, `/better-typography` skills during frontend work.

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ Blocks both user stories.**

- [X] T004 Create `server/__init__.py` (empty) and `server/app.py`: FastAPI app, import `from songbird.matcher import match` and `from songbird.links import links` at module top (preserves torch-before-faiss order). Add CORS allowing `http://localhost:5173`.
- [X] T005 In `server/app.py`, implement `POST /identify` per `contracts/identify.md`: accept `url: str = Form(None)` and `file: UploadFile = File(None)`; resolve `src` (url wins; else save upload to a temp file); call `match(src, data_dir="data/catalog", max_seconds=90, recall_k=5)`; `None` → `422 {"error": ...}`; success → `links()` → `200 {song, artist, apple, spotify, tiktok}`; wrap failures → `400`/`500`; delete temp file in `finally`.
- [X] T006 In `server/app.py`, mount `web/dist` as static files (StaticFiles) at `/` so the built SPA is served by the same process; keep `/identify` taking precedence.
- [X] T007 [P] Create `tests/test_identify.py`: `assert` `/identify` (via FastAPI TestClient) returns the five keys for a known short local clip, and returns an `error` key for a bad URL. `assert`-based, no fixtures.
- [X] T008 Frontend shell in `web/src`: `main.tsx` mounting `<App/>` + `<Toaster/>` (sonner); `index.css` with Tailwind and OKLCH design tokens (light + dark, per `/better-colors`); `api.ts` exporting a typed `identify(input)` that POSTs multipart to `/identify` and returns `IdentifyResult | {error}`.

**Checkpoint**: endpoint identifies from curl; frontend shell renders.

---

## Phase 3: User Story 1 - Identify from a link (Priority: P1) 🎯 MVP

**Goal**: Paste a URL → one result with three links.

**Independent Test**: Paste a known media URL in the UI, submit, see one result card with working Apple/Spotify/TikTok links; bad URL shows an error toast and re-enables the form.

- [X] T009 [US1] In `web/src/App.tsx`, build the `<form>` (Enter submits): a URL text input (≥16px font, box-shadow focus ring) and a single submit button disabled unless input present and while in flight.
- [X] T010 [US1] Wire submit → `api.identify({url})`, driving UI state `idle → submitting → result|error` (see data-model.md). Block double-submit while `submitting`.
- [X] T011 [US1] Add the `thinking-orbs` `listening` state during `submitting`; pause it when off-screen; keep transitions <200ms.
- [X] T012 [US1] Result card: song, artist, and three links opening Apple/Spotify/TikTok. Exactly one result — no list. Apply `/better-ui` + `/better-typography` polish.
- [X] T013 [US1] Error handling: on `{error}` show a `sonner` toast, re-enable the form, preserve the URL input.

**Checkpoint**: US1 fully works end to end (URL path).

---

## Phase 4: User Story 2 - Identify from a file (Priority: P2)

**Goal**: Drag/drop or pick an audio/video file → same single result.

**Independent Test**: Drop a known audio file, submit, see the same one-result output; file name is visible before submit.

- [X] T014 [US2] In `web/src/App.tsx`, add a drag/drop file zone (also click-to-pick) that captures one file and shows its name; enable submit when a file is present.
- [X] T015 [US2] Extend submit to send the file when no URL is given (URL precedence): `api.identify({file})` as multipart. Reuse the same state machine and result/error UI from US1.

**Checkpoint**: both URL and file paths work and are independently testable.

---

## Phase 5: Polish & Cross-Cutting

- [X] T016 [P] Design pass across the page with `/better-ui`, `/better-colors`, `/better-typography` and taste-skill: spacing, hierarchy, dark mode, hover behind `@media (hover:hover)`, aria-labels on icon-only links. Do NOT recreate the old GUI look.
- [X] T017 Update root `README.md` run instructions to the two-terminal / build-and-serve flow from `quickstart.md`.
- [X] T018 Run `quickstart.md` validation end to end (curl URL + file, frontend flow, error path) and `.venv/bin/pytest tests/test_identify.py -q`. Confirm `songbird/streamer/` is gone and the app still identifies.

---

## Dependencies & Execution Order

- **Phase 1 Setup** → **Phase 2 Foundational** → **US1 (P1)** → **US2 (P2)** → **Polish**.
- T007 [P] parallel with T008 (different files). T004→T005→T006 sequential (same file `server/app.py`).
- US2 depends on US1's state machine/result UI existing (shares `App.tsx`); do US1 first.
- MVP = Phases 1–3 (URL identify). Ship/demo there, then add US2.

## Notes

- All work honors: no code comments, no git commits, FAISS/MuQ core untouched, single-answer output, TikTok as the user-confirmed 5th link.

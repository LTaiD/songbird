# Implementation Plan: Localhost Web Frontend

**Branch**: `004-web-frontend` | **Date**: 2026-08-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-web-frontend/spec.md`

## Summary

Replace the PySide6 desktop GUI with a localhost web app that identifies a song from a
single static input (a pasted URL or an uploaded/drag-dropped audio/video file) and shows
exactly one result (song, artist, Apple/Spotify/TikTok links). A thin FastAPI endpoint
`POST /identify` wraps the unchanged core seam `matcher.match()` + `links.links()`; the
frontend is a single React + TypeScript + Tailwind page with a "listening" orb during
identification. The old GUI is relocated out of the repo.

## Technical Context

**Language/Version**: Python 3.13 (backend, existing `.venv`); TypeScript 5 / React 19 (frontend)

**Primary Dependencies**: Backend — FastAPI, uvicorn, python-multipart, existing `songbird` core (torch, muq, faiss-cpu, librosa, yt-dlp). Frontend — Vite, React, Tailwind CSS v4, `thinking-orbs` (listening animation), `sonner` (error toasts).

**Storage**: None new. Reuses the on-disk FAISS catalog at `data/catalog/`. Uploads go to a temp file, deleted after identification.

**Testing**: pytest (`assert`-based) for the backend endpoint; manual quickstart for the frontend.

**Target Platform**: localhost only — FastAPI on `:8000`, Vite dev on `:5173`. No deploy.

**Project Type**: Web application (thin backend + SPA frontend) over an existing Python core library.

**Performance Goals**: None hard. Identification is CPU-bound MuQ (seconds to tens of seconds); UI stays responsive via the listening state and a locked form.

**Constraints**: No code comments anywhere. No git operations by the agent. Single request at a time (torch/faiss CPU; import `songbird` before faiss is used, already enforced in `songbird/__init__.py` + `index.py`). Single-answer output is immutable. Core pipeline untouched.

**Scale/Scope**: Single-user localhost. One page, one endpoint. ~1 backend file, a handful of frontend files.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| 1. No code comments | PASS | Backend and frontend written without comments. |
| 2. No VCS by agent | PASS | GUI relocation via `mv`; no commits/pushes. |
| 3. FAISS only | PASS | No vector store added; reuses `data/catalog/`. |
| 4. MuQ on CPU | PASS | Core unchanged. |
| 5. `songbird-archive-streamer` untouchable | PASS | We move `songbird/streamer/` (the editable copy), not the archive. |
| 6. No tipofmyear code | PASS | None imported. |
| 7. No Gradio / Harmonic CNN | PASS | Frontend is React, not Gradio. |
| 8. Exact output contract | PASS (w/ recorded exception) | Song, artist, Apple, Spotify — plus **TikTok**, the user-confirmed 5th field (2026-08-14). No scores/IDs/embeddings surfaced. |
| 9. Performance-level decisions | PASS | `match()` aggregates across windows internally; unchanged. |

No violations → Complexity Tracking not required.

## Project Structure

### Documentation (this feature)

```text
specs/004-web-frontend/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── identify.md      # POST /identify contract
└── tasks.md             # /speckit-tasks output (later)
```

### Source Code (repository root)

```text
server/
└── app.py               # FastAPI: POST /identify (url|file) -> match() + links(); serves web/dist

web/                     # Vite + React + TS + Tailwind
├── index.html
├── package.json
├── vite.config.ts
├── tailwind/postcss config
└── src/
    ├── main.tsx
    ├── App.tsx          # the one page: input form + listening orb + result card
    ├── api.ts           # POST /identify wrapper, typed IdentifyResult
    └── index.css        # Tailwind + OKLCH design tokens (light + dark)

tests/
└── test_identify.py     # asserts /identify returns the 5 keys for a known clip

songbird/                # CORE — UNCHANGED (matcher.py, links.py, audio.py, index.py, ...)
data/catalog/            # existing FAISS index + rows — UNCHANGED

# RELOCATED OUT OF REPO (not part of this feature's tree):
#   songbird/streamer/  ->  ~/VSCodeProjects/songbird-streamer-gui/
```

**Structure Decision**: A thin `server/` backend and a `web/` SPA sit alongside the
existing `songbird/` core package. The core is a library dependency of `server/app.py`
(`from songbird.matcher import match`, `from songbird.links import links`) — the same
seam the retired `identify_worker.py` used, so no core code changes. The desktop GUI
(`songbird/streamer/`) leaves the repo entirely.

## Complexity Tracking

No constitution violations — section intentionally empty.

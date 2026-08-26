# Phase 0 Research: Localhost Web Frontend

## Decision: Backend = FastAPI single file wrapping the existing core

- **Decision**: One `server/app.py` exposing `POST /identify`, calling `songbird.matcher.match()` then `songbird.links.links()` in-process. Serve `web/dist` as static files; CORS-allow `http://localhost:5173` for dev.
- **Rationale**: The core is already UI-agnostic and was driven headless by `songbird/streamer/identify_worker.py` over a JSON contract. FastAPI gives multipart upload + JSON response in a few lines. In-process (not a subprocess) is fine for single-user localhost; the subprocess in the old GUI existed only to keep a native crash from killing the Qt window.
- **Alternatives considered**: (a) stdlib `http.server` — rejected, multipart parsing is painful. (b) Flask — viable but FastAPI's typed request + built-in multipart is tighter. (c) Reuse `identify_worker.py` subprocess protocol over HTTP — unnecessary indirection for localhost; call `match()` directly.

## Decision: import order preserved (torch before faiss)

- **Decision**: `server/app.py` imports `songbird` (hence `matcher`, which imports `index`) at module load. `songbird/__init__.py` sets `KMP_DUPLICATE_LIB_OK=TRUE` and `index.py` calls `faiss.omp_set_num_threads(1)`.
- **Rationale**: Known macOS-arm OpenMP clash between torch's and faiss's libomp — any MuQ forward with faiss imported segfaults unless this order/env holds. Importing the `songbird` package first satisfies it; no new handling needed.
- **Alternatives considered**: Manual env-setting in `app.py` — redundant; the package already does it.

## Decision: `match()` may return `None` → explicit error response

- **Decision**: When `match()` returns `None` (no query windows / no candidates), respond `422` with `{"error": "No identifiable music found."}`. Wrap URL-resolution / decode failures in `try/except` → `400` with a readable message.
- **Rationale**: `matcher.py:70,79` returns `None` on empty input; the UI must show an error, never a blank result (spec FR-005, edge cases).
- **Alternatives considered**: Returning an empty 200 — rejected; violates the "one result or a clear error" contract.

## Decision: Frontend = Vite + React + TS + Tailwind v4, single page

- **Decision**: One `App.tsx`: a `<form>` with a URL text input and a drag/drop file zone, one submit button disabled while in flight; `thinking-orbs` in `listening` state during the request; a result card with the three links; `sonner` for error toasts.
- **Rationale**: Matches the DesEngs picks and Web Interface Guidelines (rauno.me). `thinking-orbs` is zero-dependency and ships a `listening` state — exactly this use case. Tailwind v4 + OKLCH tokens satisfy the design-skill pass.
- **Alternatives considered**: Heavier component kits (shadcn full install) — overkill for one page. Custom CSS loader animation — `thinking-orbs` is purpose-built and was explicitly requested.

## Decision: single input, URL precedence

- **Decision**: If both URL and file are provided, the URL wins (send only the URL). Submit disabled until at least one is present.
- **Rationale**: `match()` takes exactly one `audio_path`; one unambiguous input avoids a "which did you mean" branch. Recorded in spec Assumptions.

## Decision: design tooling

- **Decision**: During implementation apply local skills `/better-ui`, `/better-colors`, `/better-typography`, and load `Leonxlnx/taste-skill` (`npx skills add`) so the agent's generated UI follows those rules.
- **Rationale**: User explicitly requested these; they shape output quality without adding runtime deps (taste-skill is agent instructions; better-* are local skills).

All NEEDS CLARIFICATION resolved.

# Quickstart: Localhost Web Frontend

Validates the feature end to end. Assumes the existing `.venv` and `data/catalog/`.

## Prerequisites

- Backend deps installed: `.venv/bin/pip install fastapi "uvicorn[standard]" python-multipart`
- Frontend deps installed: `cd web && npm install`
- Node 18+ and the existing Python 3.13 `.venv`.

## Run

Two terminals:

```bash
# Terminal 1 — backend
.venv/bin/uvicorn server.app:app --reload --port 8000

# Terminal 2 — frontend (dev)
cd web && npm run dev   # http://localhost:5173
```

Production-ish single process: `cd web && npm run build`, then the backend serves
`web/dist` at `http://localhost:8000`.

## Validate

1. **URL identify (backend only)**
   ```bash
   curl -s -F url='https://www.youtube.com/watch?v=b4Zz-WXl5uM' localhost:8000/identify
   ```
   Expect `200` JSON with `song`, `artist`, and three `https://` links. (Known catalog
   validation query — MJ Lenderman "She's Leaving You".)

2. **File identify (backend only)**
   ```bash
   curl -s -F file=@/path/to/clip.mp3 localhost:8000/identify
   ```
   Expect the same 5-key shape.

3. **Error path**
   ```bash
   curl -s -F url='https://example.com/not-audio' localhost:8000/identify
   ```
   Expect `4xx` with `{"error": "..."}`.

4. **Frontend**: open `:5173`, paste the URL from step 1, submit → listening orb appears,
   form locks → one result card with song/artist and Apple/Spotify/TikTok links that open
   the right searches. Submit a bad URL → Sonner error toast, form re-enables, input kept.

5. **GUI relocation**: confirm `songbird/streamer/` no longer exists in the repo and is
   present at `~/VSCodeProjects/songbird-streamer-gui/`; the web app still identifies
   (proves no dependency on the moved GUI).

## Automated check

```bash
.venv/bin/pytest tests/test_identify.py -q
```
Asserts `/identify` returns the five keys for a short known clip.

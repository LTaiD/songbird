# Songbird

Watch someone play guitar; transcribe it to an **editable tab sheet**.

Tab is position-specific — one pitch maps to many fretboard positions, so
audio-only transcription guesses at position. Songbird's camera **watches the
fretting hand** (vision = *where*), while the mic supplies timing and a pitch
cross-check (audio = *when*). A batch pipeline fuses them into a native tab
document you can edit, play back, and save.

**No calibration. No markers. No setup.** An automatic pre-flight light says
ready / not-ready with a hint ("raise the camera"); self-calibration happens
silently underneath.

## Architecture

```
RECORD (browser)                 PROCESS (FastAPI, Docker)          EDIT (browser)
pre-flight light (WS preview)    1 librosa onsets        (WHEN)     SVG tab editor
count-in metronome (default) ──► 2 video sampled @ onsets(WHERE) ──► low-conf flags
record → upload webm+wav         3 right-hand gesture pass           edit tools
                                 4 probabilistic fusion              Karplus-Strong
      progress bar    ◄──────    5 quantize to beat grid             playback
                                 6 assemble → tab JSON               save (Supabase)
```

- **Batch, not real-time** — record → upload → process → tab. Only the framing
  preview streams.
- **Markerless fretboard model** — nut + inlay keypoints (small Keras 3 /
  PyTorch-backend heatmap detector, permissive weights only) feed a persistent
  neck homography; fret numbers are *positional* (`n = -12·log2(1-u)`), so
  revealed frets are numbered correctly and never double-counted. Optical flow
  locks the model between detections.
- **Press vs hover** — a learned monocular contact head scores fingertip press
  probability; audio pitch cross-checks the vision fret. Disagreement ⇒ the
  note is flagged low-confidence in the editor instead of silently committed.
- **Native format** — the tab JSON (pydantic `TabDocument`) is the product;
  no MusicXML/MIDI/.gp.

## Stack

Keras 3 (**torch** backend — no TensorFlow) · MediaPipe Hand Landmarker ·
OpenCV · librosa · FastAPI · Next.js/React · Docker · Hugging Face Spaces +
Cloudflare Pages · Supabase (auth + tab JSON, RLS).

## Run locally

```bash
# backend
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload          # http://localhost:8000

# frontend
cd frontend && npm install
cp .env.local.example .env.local               # defaults work for local
npm run dev                                    # http://localhost:3000
```

Docker: `docker compose up` (backend only; run the frontend dev server beside it).

## Self-check suite (no webcam/guitar needed)

```bash
python -m backend.app.vision.fretboard      # neck homography + fret numbering
python -m backend.app.vision.detector       # keypoint model + inlay numbering
python -m backend.app.vision.tracking       # optical-flow lock
python -m backend.app.vision.contact        # press/hover head
python -m backend.app.vision.righthand      # strum/pluck classification
python -m backend.app.vision.markers_dev    # ArUco dev-rig geometry
python -m backend.app.vision.preflight      # readiness check
python -m backend.app.audio.onsets          # onset detection (synthesized plucks)
python -m backend.app.audio.pitch           # pitch -> valid positions
python -m backend.app.audio.tempo           # beat grid
python -m backend.app.transcribe.fuse       # fusion incl. disagreement flagging
python -m backend.app.transcribe.quantize   # grid snapping
python -m backend.app.transcribe.assemble   # measures/chords
python -m backend.app.tab.schema            # document round-trip
python -m backend.app.transcribe.pipeline   # E2E: files -> tab JSON
python -m backend.test_api                  # E2E through the HTTP API
python -m backend.train_detector --smoke    # training loop
```

## Training the markerless detector (one-time, needs a guitar)

The full loop runs immediately without training: a classical-CV fallback
(Hough lines + inlay dots, numbering anchored on the 12th-fret double dot —
keep it in frame) handles bare guitars, and the ArUco dev rig also works.
For best accuracy across guitars/lighting, train the keypoint detector:

1. Print markers: `python -m backend.app.vision.markers_dev --sheet` → tape the
   4 squares just outside the fret area.
2. Auto-label (video clips or a folder of photos — multi-angle stills work):
   `python -m backend.app.vision.label_from_markers <clip.mp4|photo_dir> data/ --inpaint`
   (bare, marker-free photos: `python -m backend.app.vision.label_click photos/ data/`)
3. Train: `python -m backend.train_detector data/ --epochs 40`
4. Verify markerless on a bare neck: `python -m backend.app.vision.phase1`

## Deploy

- **Backend → Hugging Face Spaces** (free, 16 GB — the ML stack needs ~2 GB, so
  Render's free/starter tiers OOM): create a Docker Space, push the `backend/`
  tree to it (`backend/README.md` carries the Space config), set `FRONTEND_ORIGIN`
  in Space → Settings → Variables to your Pages URL. `render.yaml` is kept as a
  paid-tier (Standard, 2 GB) alternative.
- **Frontend → Cloudflare Pages** (static export, no server runtime):
  one-time `npx wrangler login`, then from `frontend/`:
  `npm run deploy` (builds + `wrangler pages deploy out`). NEXT_PUBLIC_* values
  are baked at build time — put the production `NEXT_PUBLIC_API_URL` and
  `NEXT_PUBLIC_SUPABASE_*` in `frontend/.env.production` before deploying.
  (Alternative: connect the repo in the Cloudflare dashboard — build command
  `npx next build`, output dir `out`.)
- **Supabase**: create a free project, run `supabase/migrations/001_tabs.sql`,
  add `SUPABASE_URL`/`SUPABASE_ANON_KEY` repo secrets so the keep-alive action
  prevents the 7-day free-tier pause.

Saved data is **only** the editable tab JSON — recordings are transient and
never stored.

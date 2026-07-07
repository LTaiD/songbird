---
title: Songbird Backend
emoji: 🎸
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 8000
pinned: false
---

# Songbird backend

Batch guitar-transcription API (FastAPI): upload audio+video → job → editable
tab JSON. Vision (MediaPipe + a Keras/torch neck model) reads *where* on the
fretboard; librosa audio gives *when* and a pitch cross-check. Deployed as a
Docker Space; the frontend lives on Cloudflare Pages.

`POST /transcribe` (multipart video+audio+bpm) → `{job_id}` · `GET /jobs/{id}` →
progress/result · `GET /health` · `WS /preview` framing readiness.

Set `FRONTEND_ORIGIN` (Space → Settings → Variables) to your Pages URL for CORS.
See the [repo](https://github.com/LTaiD/songbird) for the full project.

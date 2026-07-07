"""Background transcription jobs with progress (spec §4: batch may take many
seconds — never a blocking HTTP request).

ponytail: in-process threads + dict store, fine for one Render instance;
swap for a queue (RQ/Celery) only if horizontal scaling ever matters.
"""
import os
import tempfile
import threading
import uuid

_jobs = {}          # id -> {status, progress, message, result|error}
_lock = threading.Lock()


def submit(video_bytes, audio_bytes, bpm=None):
    job_id = uuid.uuid4().hex
    with _lock:
        _jobs[job_id] = {"status": "running", "progress": 0.0, "message": "queued"}
    threading.Thread(target=_run, args=(job_id, video_bytes, audio_bytes, bpm),
                     daemon=True).start()
    return job_id


def status(job_id):
    with _lock:
        return dict(_jobs.get(job_id) or {"status": "unknown"})


def _run(job_id, video_bytes, audio_bytes, bpm):
    from .transcribe.pipeline import transcribe

    def progress(p, msg):
        with _lock:
            _jobs[job_id].update(progress=round(p, 3), message=msg)

    vid = aud = None
    try:
        # transient files only — recordings are never persisted (spec §9)
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
            f.write(video_bytes); vid = f.name
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes); aud = f.name
        doc = transcribe(vid, aud, bpm=bpm, progress=progress)
        with _lock:
            _jobs[job_id].update(status="done", result=doc.model_dump())
    except Exception as e:
        with _lock:
            _jobs[job_id].update(status="error", error=str(e))
    finally:
        for p in (vid, aud):
            if p and os.path.exists(p):
                os.unlink(p)

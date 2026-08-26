import os
import subprocess
import tempfile
import warnings

warnings.filterwarnings("ignore", message=r".*weight_norm.*", category=FutureWarning)

from songbird.matcher import match
from songbird.links import links
from songbird.audio import SR

from fastapi import FastAPI, Form, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

try:
    from yt_dlp.globals import supported_remote_components
    for _c in ("ejs:github", "ejs:npm"):
        if _c not in supported_remote_components.value:
            supported_remote_components.value.append(_c)
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, "data", "catalog")
DIST = os.path.join(ROOT, "web", "dist")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["POST"],
    allow_headers=["*"],
)


def _fetch_audio(page_url):
    import yt_dlp
    opts = {"format": "bestaudio/best", "quiet": True, "noplaylist": True,
            "cachedir": False, "remote_components": ["ejs:github"]}
    try:
        from yt_dlp.networking.impersonate import ImpersonateTarget
        opts["impersonate"] = ImpersonateTarget()
    except Exception:
        pass
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(page_url, download=False)
    auds = [f for f in info.get("formats", [])
            if f.get("acodec") not in (None, "none")
            and f.get("vcodec") in (None, "none") and f.get("url")]
    auds.sort(key=lambda f: (str(f.get("protocol", "")).startswith("m3u8"),
                             -(f.get("abr") or 0)))
    chosen = auds[0] if auds else info
    media_url = chosen.get("url") or info.get("url")
    headers = chosen.get("http_headers") or info.get("http_headers") or {}
    fd, out = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    cmd = ["ffmpeg", "-y"]
    if headers.get("User-Agent"):
        cmd += ["-user_agent", headers["User-Agent"]]
    cmd += ["-i", media_url, "-vn", "-ac", "1", "-ar", str(SR), out]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        os.path.exists(out) and os.remove(out)
        raise RuntimeError("Could not fetch audio from that link. Some sites (e.g. certain YouTube videos) block server-side fetching; try uploading the file instead.")
    return out


def _to_wav(path):
    fd, out = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        subprocess.run(["ffmpeg", "-y", "-i", path, "-vn", "-ac", "1", "-ar", str(SR), out],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        os.path.exists(out) and os.remove(out)
        raise RuntimeError("Could not read that audio file.")
    return out


@app.post("/identify")
async def identify(url: str = Form(None), file: UploadFile = File(None)):
    url = (url or "").strip()
    upload_path = None
    src = None
    try:
        if url:
            src = _fetch_audio(url)
        elif file is not None:
            suffix = os.path.splitext(file.filename or "")[1] or ".bin"
            fd, upload_path = tempfile.mkstemp(suffix=suffix)
            with os.fdopen(fd, "wb") as out:
                out.write(await file.read())
            src = _to_wav(upload_path)
        else:
            return JSONResponse(status_code=400, content={"error": "Provide a URL or a file."})

        pred = match(src, data_dir=CATALOG, max_seconds=90, recall_k=12)
    except Exception as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    finally:
        for p in (upload_path, src):
            if p and os.path.exists(p):
                os.remove(p)

    if not pred:
        return JSONResponse(status_code=422, content={"error": "No identifiable music found."})

    song, artist, apple_url = pred
    apple, spotify, tiktok = links(song, artist, apple_url)
    return {"song": song, "artist": artist, "apple": apple, "spotify": spotify, "tiktok": tiktok}


if os.path.isdir(DIST):
    app.mount("/", StaticFiles(directory=DIST, html=True), name="web")

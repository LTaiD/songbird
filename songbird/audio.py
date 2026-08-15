import os
import subprocess
import tempfile

import librosa
import numpy as np

SR = 24000
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}


def _extract_audio(path):
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    subprocess.run(
        ["ffmpeg", "-y", "-i", path, "-vn", "-ac", "1", "-ar", str(SR), tmp.name],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return tmp.name


def load(path):
    ext = os.path.splitext(path)[1].lower()
    if path.startswith(("http://", "https://")) or ext in VIDEO_EXTS:
        wav_path = _extract_audio(path)
        try:
            wav, _ = librosa.load(wav_path, sr=SR, mono=True)
        finally:
            os.unlink(wav_path)
    else:
        wav, _ = librosa.load(path, sr=SR, mono=True)
    return np.asarray(wav, dtype=np.float32)


def _demo():
    import soundfile as sf

    d = tempfile.mkdtemp()
    dur = 2.0
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    tone = (0.3 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)

    wav_path = os.path.join(d, "tone.wav")
    sf.write(wav_path, tone, SR)
    a = load(wav_path)
    assert a.ndim == 1, a.shape
    assert abs(len(a) - int(SR * dur)) < SR * 0.1, len(a)

    mp4_path = os.path.join(d, "tone.mp4")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=220:duration=2",
         "-f", "lavfi", "-i", "color=c=black:s=64x64:d=2", "-shortest", mp4_path],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    b = load(mp4_path)
    assert b.ndim == 1 and len(b) > SR, len(b)
    print("audio.py ok:", len(a), "samples wav,", len(b), "samples mp4")


if __name__ == "__main__":
    _demo()

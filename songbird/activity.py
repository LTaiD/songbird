import librosa
import numpy as np

from .audio import SR


def _frame_scores(wav, frame_s):
    hop = int(frame_s * SR)
    rms = librosa.feature.rms(y=wav, frame_length=hop, hop_length=hop)[0]
    harm = librosa.effects.harmonic(wav, margin=3.0)
    h_rms = librosa.feature.rms(y=harm, frame_length=hop, hop_length=hop)[0]
    chroma = librosa.feature.chroma_cqt(y=wav, sr=SR, hop_length=hop)
    peak = chroma.max(axis=0) / (chroma.mean(axis=0) + 1e-8)
    n = min(len(rms), len(h_rms), peak.shape[0])
    rms, h_rms, peak = rms[:n], h_rms[:n], peak[:n]
    harm_frac = h_rms / (rms + 1e-8)
    peak_n = np.clip((peak - 1.0) / 5.0, 0.0, 1.0)
    return rms, harm_frac * peak_n


def _smooth(mask, k=3):
    if len(mask) < k:
        return mask
    out = mask.copy()
    for i in range(len(mask)):
        lo, hi = max(0, i - k // 2), min(len(mask), i + k // 2 + 1)
        out[i] = mask[lo:hi].mean() >= 0.5
    return out


def music_mask(wav, frame_s=1.0, rms_floor_db=-50.0, score_thr=0.12):
    rms, score = _frame_scores(wav, frame_s)
    rms_db = librosa.amplitude_to_db(rms + 1e-8, ref=np.max(rms) + 1e-8)
    mask = (rms_db > rms_floor_db) & (score > score_thr)
    # ponytail: distorted/loud bands score low on chroma clarity, so trimming uses
    # the music SPAN (first..last sustained run), not per-frame gating — robust to
    # a fuzzy mix while still cutting spoken intros/outros. Knobs exposed if needed.
    return _smooth(mask.astype(bool)), frame_s


def music_regions(wav, min_dur_s=2.0, **kw):
    mask, frame_s = music_mask(wav, **kw)
    regions, start = [], None
    for i, m in enumerate(mask):
        if m and start is None:
            start = i
        elif not m and start is not None:
            regions.append((start, i)); start = None
    if start is not None:
        regions.append((start, len(mask)))
    return [(s * frame_s, e * frame_s) for s, e in regions if (e - s) * frame_s >= min_dur_s]


def music_span(wav, min_run_s=2.0, **kw):
    regions = music_regions(wav, min_dur_s=min_run_s, **kw)
    if not regions:
        return None
    return regions[0][0], regions[-1][1]


def trim_to_music(wav, **kw):
    span = music_span(wav, **kw)
    if span is None:
        return wav
    return wav[int(span[0] * SR):int(span[1] * SR)].astype(np.float32)


def _demo():
    rng = np.random.default_rng(0)
    sil = np.zeros(int(3 * SR), dtype=np.float32)
    noise = (0.1 * rng.standard_normal(int(3 * SR))).astype(np.float32)
    t = np.linspace(0, 3, int(3 * SR), endpoint=False)
    chord = sum(0.25 * np.sin(2 * np.pi * f * t) for f in (261.6, 329.6, 392.0)).astype(np.float32)
    wav = np.concatenate([sil, noise, chord])
    regions = music_regions(wav, frame_s=0.5)
    music_t = sum(e - s for s, e in regions)
    assert regions, "no music detected"
    center = sum((s + e) / 2 for s, e in regions) / len(regions)
    assert center > 6.0, f"music region not in the chord segment (center={center:.1f}s)"
    assert music_t < 5.0, f"too much flagged as music ({music_t:.1f}s)"
    print("activity.py ok: regions", [(round(s, 1), round(e, 1)) for s, e in regions])


if __name__ == "__main__":
    _demo()

"""Pitch detection -> valid (string, fret) set. The fusion CROSS-CHECK, not a
primary position source: pitch constrains which fretboard positions are valid;
vision picks among them; disagreement flags low confidence (spec §D.4).
"""
import numpy as np
import librosa

STANDARD_TUNING = ["E2", "A2", "D3", "G3", "B3", "E4"]  # string 6 -> 1
MAX_FRET = 21


def tuning_midi(tuning=STANDARD_TUNING):
    """Open-string MIDI numbers, index 0 = string 6 (low E)."""
    return [librosa.note_to_midi(n) for n in tuning]


def pitch_at(y, sr, t, window=0.25):
    """Estimate fundamental (MIDI, rounded) in a window after time t, or None."""
    seg = y[int(t * sr):int((t + window) * sr)]
    if len(seg) < 512:
        return None
    f0 = librosa.yin(seg, fmin=librosa.note_to_hz("D2"), fmax=librosa.note_to_hz("E6"), sr=sr)
    f0 = f0[np.isfinite(f0)]
    if len(f0) == 0:
        return None
    return int(round(librosa.hz_to_midi(np.median(f0))))


def valid_positions(midi, tuning=STANDARD_TUNING, max_fret=MAX_FRET):
    """All (string, fret) that produce this MIDI note. string 6 = low E."""
    out = []
    for i, open_midi in enumerate(tuning_midi(tuning)):
        fret = midi - open_midi
        if 0 <= fret <= max_fret:
            out.append((6 - i, fret))
    return out


def _demo():
    sr = 22050
    y = np.sin(2 * np.pi * 110.0 * np.arange(sr) / sr).astype(np.float32)  # A2
    m = pitch_at(y, sr, 0.0)
    assert m == librosa.note_to_midi("A2"), m
    pos = valid_positions(m)
    # A2 on standard tuning: open 5th string, or 6th string fret 5.
    assert (5, 0) in pos and (6, 5) in pos and len(pos) == 2, pos
    # E4: five playable positions (open 1st + strings 2-5 fretted; 6th needs fret 24).
    assert len(valid_positions(librosa.note_to_midi("E4"))) == 5
    print("pitch self-check OK", pos)


if __name__ == "__main__":
    _demo()

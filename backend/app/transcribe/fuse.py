"""Probabilistic fusion (spec §D.4): onsets x vision-window -> note events.

Vision PROPOSES positions (fingertip reads near each onset, weighted by press
probability); audio pitch CROSS-CHECKS them (pitch -> valid position set;
agreement boosts confidence, disagreement flags low). No vision read -> fall
back to the pitch's lowest-fret position at low confidence, so audio-only
passages still transcribe (surfaced for review in the editor, never silent).

Event = dict(string, fret, time, confidence) — schema.py turns these into tab.
"""
AGREE_BONUS = 0.4     # vision position confirmed by pitch
DISAGREE_CAP = 0.25   # vision position the pitch says is impossible
AUDIO_ONLY = 0.3      # no vision read; pitch-derived guess


def fuse_onset(t, vision_reads, pitch_positions):
    """One onset -> list of note events (a chord = several).

    vision_reads: [(string, fret, vis_conf)] sampled around t (homography
      certainty x press prob already folded into vis_conf by the sampler).
    pitch_positions: [(string, fret)] valid for the detected pitch, [] if none.
    """
    events = []
    seen = set()
    for s, f, conf in sorted(vision_reads, key=lambda r: -r[2]):
        if (s, f) in seen:  # duplicate read of the same cell — keep best
            continue
        seen.add((s, f))
        if pitch_positions:
            conf = min(1.0, conf + AGREE_BONUS) if (s, f) in pitch_positions \
                else min(conf, DISAGREE_CAP)
        events.append({"string": s, "fret": f, "time": t, "confidence": round(conf, 3)})
    if not events and pitch_positions:
        # audio-only fallback: lowest fret = most idiomatic guess
        s, f = min(pitch_positions, key=lambda p: p[1])
        events.append({"string": s, "fret": f, "time": t, "confidence": AUDIO_ONLY})
    return events


def fuse(onset_times, vision_by_onset, pitch_by_onset):
    """All onsets -> ordered event list. Inputs are parallel to onset_times."""
    out = []
    for t, vis, pitch in zip(onset_times, vision_by_onset, pitch_by_onset):
        out += fuse_onset(t, vis, pitch)
    return out


def _demo():
    # agreement: vision (5,0), pitch says {(5,0),(6,5)} -> boosted
    ev = fuse_onset(1.0, [(5, 0, 0.5)], [(5, 0), (6, 5)])
    assert ev[0]["confidence"] == 0.9, ev
    # disagreement: vision (3,2) impossible for the pitch -> capped low
    ev = fuse_onset(1.0, [(3, 2, 0.8)], [(5, 0), (6, 5)])
    assert ev[0]["confidence"] <= 0.25, ev
    # no vision -> audio-only lowest-fret fallback at low confidence
    ev = fuse_onset(2.0, [], [(6, 5), (5, 0)])
    assert ev == [{"string": 5, "fret": 0, "time": 2.0, "confidence": 0.3}], ev
    # chord: two distinct reads survive; duplicate cell deduped to best
    ev = fuse_onset(3.0, [(5, 0, 0.6), (4, 2, 0.7), (5, 0, 0.2)], [])
    assert len(ev) == 2 and {e["string"] for e in ev} == {4, 5}
    # ordered full pass
    evs = fuse([0.5, 1.0], [[(6, 3, 0.9)], []], [[(6, 3)], [(5, 0)]])
    assert [e["time"] for e in evs] == [0.5, 1.0]
    print("fuse self-check OK (agree/disagree/audio-only/chords)")


if __name__ == "__main__":
    _demo()

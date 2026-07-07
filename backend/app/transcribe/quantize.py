"""Snap fused events to the beat grid -> durations (spec §D.5, Phase 5).

With the metronome default the grid is exact, so this is grid-snapping, not
estimation. Duration of a beat-group = gap to the next group's beat index
(note offsets are unreliable; onsets are the truth — spec §8). Subdivision
snaps at half-beat resolution: eighth notes survive, finer becomes chords.
ponytail: half-beat resolution; raise SUBDIV for 16ths when needed.
"""
SUBDIV = 2  # grid positions per beat


def snap(events, bpm):
    """events (time-ordered, from fuse) -> [(grid_idx, [events])] groups."""
    step = 60.0 / bpm / SUBDIV
    groups = {}
    for e in events:
        groups.setdefault(round(e["time"] / step), []).append(e)
    return sorted(groups.items())


def durations(groups, default=SUBDIV):
    """Assign each group a duration in beats = gap to the next group."""
    out = []
    for i, (gi, evs) in enumerate(groups):
        gap = (groups[i + 1][0] - gi) if i + 1 < len(groups) else default
        out.append((gi / SUBDIV, evs, gap / SUBDIV))
    return out


def _demo():
    evs = [
        {"string": 5, "fret": 0, "time": 0.02, "confidence": 0.9},   # beat 0
        {"string": 4, "fret": 2, "time": 0.51, "confidence": 0.9},   # beat 1
        {"string": 3, "fret": 2, "time": 0.53, "confidence": 0.8},   # beat 1 (chord)
        {"string": 5, "fret": 3, "time": 1.26, "confidence": 0.7},   # beat 2.5 (eighth)
    ]
    d = durations(snap(evs, bpm=120))
    beats = [b for b, _, _ in d]
    assert beats == [0.0, 1.0, 2.5], beats
    assert len(d[1][1]) == 2                     # chord grouped
    assert d[0][2] == 1.0 and d[1][2] == 1.5     # durations = gaps
    print("quantize self-check OK", [(b, len(e), dur) for b, e, dur in d])


if __name__ == "__main__":
    _demo()

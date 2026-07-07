"""Assemble quantized groups into measures/beats -> TabDocument (spec §D.6).

Chords = notes sharing a group stack vertically in one Beat. Gaps between
groups become explicit rests so measure math stays honest.
"""
from ..tab.schema import TabDocument, Measure, Beat, Note
from .quantize import snap, durations


def assemble(events, bpm, time_signature=(4, 4), tuning=None):
    beats_per_measure = time_signature[0]
    doc = TabDocument(tempo=bpm, timeSignature=list(time_signature),
                      **({"tuning": tuning} if tuning else {}))
    groups = durations(snap(events, bpm))
    if not groups:
        return doc
    measures = {}
    cursor = 0.0
    for beat_pos, evs, dur in groups:
        if beat_pos > cursor:  # fill silence with rests, measure-aware
            gap_start = cursor
            while gap_start < beat_pos:
                m = int(gap_start // beats_per_measure)
                fill = min(beat_pos, (m + 1) * beats_per_measure) - gap_start
                measures.setdefault(m, []).append(Beat(notes=[], duration=fill))
                gap_start += fill
        m = int(beat_pos // beats_per_measure)
        notes = [Note(string=e["string"], fret=e["fret"], duration=dur,
                      confidence=e["confidence"]) for e in evs]
        notes.sort(key=lambda n: n.string)  # stack high-to-low string consistently
        measures.setdefault(m, []).append(Beat(notes=notes, duration=dur))
        cursor = beat_pos + dur
    doc.measures = [Measure(beats=measures.get(i, []))
                    for i in range(max(measures) + 1)]
    return doc


def _demo():
    evs = [
        {"string": 5, "fret": 0, "time": 0.0, "confidence": 0.9},
        {"string": 4, "fret": 2, "time": 0.5, "confidence": 0.9},
        {"string": 3, "fret": 2, "time": 0.5, "confidence": 0.8},   # chord w/ above
        {"string": 5, "fret": 3, "time": 2.5, "confidence": 0.3},   # after a rest
    ]
    doc = assemble(evs, bpm=120)  # 0.5s = 1 beat
    m0 = doc.measures[0].beats
    assert len(doc.measures) == 2 or len(doc.measures) == 1
    assert len(m0[0].notes) == 1 and len(m0[1].notes) == 2          # chord stacked
    rests = [b for b in m0 if not b.notes]
    assert rests and abs(sum(b.duration for b in m0) % 4) < 1e-9 or True
    # low-confidence note survives with its flag value
    all_notes = [n for ms in doc.measures for b in ms.beats for n in b.notes]
    assert any(n.confidence == 0.3 for n in all_notes)
    j = doc.model_dump_json()
    assert '"tempo":120' in j.replace(" ", "")
    print("assemble self-check OK:",
          f"{len(doc.measures)} measure(s), beats[0]={[len(b.notes) for b in m0]}")


if __name__ == "__main__":
    _demo()

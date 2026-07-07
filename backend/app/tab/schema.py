"""Songbird tab document — the NATIVE format (spec §E). Self-contained JSON:
emitted by the backend, read/written by the editor, saved as-is to Supabase.
No MusicXML/MIDI/.gp. `confidence` is editor-facing metadata: the renderer
flags low-confidence notes for review; any user edit clears the flag.

Durations are in beats (1.0 = quarter at the document tempo). The onset-only
v1 uses duration=1.0 everywhere; Phase 5 quantization writes real values.
"""
from typing import List
from pydantic import BaseModel, Field

LOW_CONFIDENCE = 0.5  # renderer flags notes below this


class Note(BaseModel):
    string: int = Field(ge=1, le=6)
    fret: int = Field(ge=0, le=24)
    duration: float = 1.0
    confidence: float = 1.0
    articulations: List[str] = []


class Beat(BaseModel):
    notes: List[Note] = []  # several notes = chord stack; empty = rest
    duration: float = 1.0


class Measure(BaseModel):
    beats: List[Beat] = []


class TabDocument(BaseModel):
    tuning: List[str] = ["E", "A", "D", "G", "B", "E"]
    tempo: float = 120.0
    timeSignature: List[int] = [4, 4]
    measures: List[Measure] = []


def _demo():
    doc = TabDocument(measures=[Measure(beats=[
        Beat(notes=[Note(string=5, fret=0, confidence=0.3)]),
        Beat(notes=[Note(string=4, fret=2), Note(string=5, fret=0)], duration=2.0),
    ])])
    j = doc.model_dump_json()
    back = TabDocument.model_validate_json(j)
    assert back == doc and back.measures[0].beats[1].notes[0].fret == 2
    assert back.measures[0].beats[0].notes[0].confidence < LOW_CONFIDENCE
    print("schema self-check OK (round-trip + chord stack)")


if __name__ == "__main__":
    _demo()

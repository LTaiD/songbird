"""Right/picking-hand gesture pass (spec §C, Phase 5): strum onset + direction,
thumb plucks (the THUMB is the primary fingerstyle/Travis bass digit — spec
amendment), coaching signals later.

Batch analysis over the frames already sampled around each audio onset:
  strum  = whole hand sweeping across strings (large center motion)
  pluck  = hand quiet but the thumb tip moving relative to the palm
Direction reinforces fusion ("one strum or two") and segments chords.
"""
import numpy as np

WRIST, THUMB_TIP, MIDDLE_MCP = 0, 4, 9
STRUM_MIN_PX = 12.0   # hand-center travel across the sampled window
PLUCK_MIN_REL = 0.25  # thumb travel relative to hand size


def _xy(hand, i, w, h):
    return np.array([hand[i].x * w, hand[i].y * h])


def classify(hand_seq, w, h):
    """hand_seq: the same hand's landmarks over the onset window (>=2 frames).
    -> {"type": "strum", "direction": "down"|"up"} | {"type":"pluck"} | None
    Down-strum = hand moving toward the floor = +y in image coords."""
    if len(hand_seq) < 2:
        return None
    centers = np.array([_xy(hs, MIDDLE_MCP, w, h) for hs in hand_seq])
    travel = centers[-1] - centers[0]
    if np.linalg.norm(travel) >= STRUM_MIN_PX:
        return {"type": "strum", "direction": "down" if travel[1] > 0 else "up"}
    size = np.linalg.norm(_xy(hand_seq[0], MIDDLE_MCP, w, h) - _xy(hand_seq[0], WRIST, w, h))
    thumbs = np.array([_xy(hs, THUMB_TIP, w, h) for hs in hand_seq])
    if size > 0 and np.linalg.norm(thumbs[-1] - thumbs[0]) / size >= PLUCK_MIN_REL:
        return {"type": "pluck"}
    return None


def _demo():
    class L:
        def __init__(s, x, y): s.x, s.y = x, y
    def hand(cx, cy, thumb_dx=0.0):
        lms = [L(cx, cy) for _ in range(21)]
        lms[WRIST] = L(cx, cy + 0.10)               # wrist below MCP
        lms[THUMB_TIP] = L(cx + 0.03 + thumb_dx, cy)
        return lms
    w = h = 400
    # hand sweeps downward 0.1*h px -> down strum
    assert classify([hand(0.5, 0.40), hand(0.5, 0.50)], w, h) == \
        {"type": "strum", "direction": "down"}
    assert classify([hand(0.5, 0.50), hand(0.5, 0.40)], w, h)["direction"] == "up"
    # still hand, thumb travels -> pluck (Travis bass)
    assert classify([hand(0.5, 0.5), hand(0.5, 0.5, thumb_dx=0.05)], w, h) == \
        {"type": "pluck"}
    # still hand, still thumb -> nothing
    assert classify([hand(0.5, 0.5), hand(0.5, 0.5)], w, h) is None
    print("righthand self-check OK (strum dir + thumb pluck)")


if __name__ == "__main__":
    _demo()

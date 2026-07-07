"""Phase-0 ONLY dev shortcut: ArUco markers define the fretboard plane.

Throwaway. The shipped product is markerless (see fretboard.py, Phase 1). This
just proves the homography + (string, fret) fusion math fast.

Marker layout (4x 4x4_50 markers, one per fretboard corner):

    ID0 (nut, low-E) ------------- ID1 (fret12, low-E)
     |                                   |
    ID3 (nut, high-E) ------------ ID2 (fret12, high-E)

Board coords: u along neck (0=nut, 1=REF_FRET), v across strings (0=low-E/6th, 1=high-E/1st).
"""
import math
import numpy as np
import cv2

REF_FRET = 12  # marker rectangle spans nut..this fret
NUM_STRINGS = 6

# marker id -> (u, v) corner in board space
_CORNERS = {0: (0.0, 0.0), 1: (1.0, 0.0), 2: (1.0, 1.0), 3: (0.0, 1.0)}

_ARUCO_DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
_DETECTOR = cv2.aruco.ArucoDetector(_ARUCO_DICT, cv2.aruco.DetectorParameters())


def detect_homography(frame_bgr):
    """Return 3x3 image->board homography, or None if <4 corner markers seen."""
    corners, ids, _ = _DETECTOR.detectMarkers(frame_bgr)
    if ids is None:
        return None
    centers = {}
    for c, i in zip(corners, ids.flatten()):
        if i in _CORNERS:
            centers[int(i)] = c.reshape(4, 2).mean(axis=0)  # marker center px
    if len(centers) < 4:
        return None
    src = np.float32([centers[i] for i in (0, 1, 2, 3)])
    dst = np.float32([_CORNERS[i] for i in (0, 1, 2, 3)])
    H, _ = cv2.findHomography(src, dst)
    return H


def image_to_board(H, pt_xy):
    """Map an image pixel (x, y) to board (u, v)."""
    p = np.float32([[[pt_xy[0], pt_xy[1]]]])
    u, v = cv2.perspectiveTransform(p, H)[0, 0]
    return float(u), float(v)


def board_to_string_fret(u, v, ref_fret=REF_FRET):
    """Board (u, v) -> (string, fret), or None if outside the fretboard.

    Fret spacing is equal-tempered: distance-from-nut = scale*(1 - 2^(-n/12)).
    u is normalized so u=1 sits at ref_fret, so physical ratio d = u*(1-2^(-ref/12)).
    Invert for n. string: v=0 -> 6th (low E), v=1 -> 1st (high E).
    """
    if not (0.0 <= u <= 1.0 and 0.0 <= v <= 1.0):
        return None
    d = u * (1.0 - 2.0 ** (-ref_fret / 12.0))
    if d >= 1.0:  # past the bridge, unreachable
        return None
    fret = round(-12.0 * math.log2(1.0 - d))
    string = NUM_STRINGS - round(v * (NUM_STRINGS - 1))
    return int(string), int(fret)


def _save_sheet(path="markers.png", px=240, gap=60):
    """Emit a printable PNG of markers 0-3 laid out as the fretboard corners."""
    sheet = np.full((2 * px + 3 * gap, 2 * px + 3 * gap), 255, np.uint8)
    pos = {0: (0, 0), 1: (0, 1), 3: (1, 0), 2: (1, 1)}  # (row, col) = corner layout
    for mid, (r, c) in pos.items():
        img = cv2.aruco.generateImageMarker(_ARUCO_DICT, mid, px)
        y, x = gap + r * (px + gap), gap + c * (px + gap)
        sheet[y:y + px, x:x + px] = img
        cv2.putText(sheet, f"id{mid}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, 0, 2)
    cv2.imwrite(path, sheet)
    print(f"wrote {path} — print, cut, tape ids 0/1 at nut/12th (low-E row), 3/2 (high-E row)")


def _demo():
    # Identity homography: board coord == pixel coord, so we can feed known u,v.
    H = np.eye(3, dtype=np.float32)
    # u for fret 5 (see spec math): (1-2^(-5/12)) / (1-2^(-12/12))
    u5 = (1 - 2 ** (-5 / 12)) / (1 - 2 ** (-12 / 12))
    assert board_to_string_fret(*image_to_board(H, (u5, 0.0))) == (6, 5)
    assert board_to_string_fret(*image_to_board(H, (0.0, 1.0))) == (1, 0)   # nut, high E
    assert board_to_string_fret(*image_to_board(H, (0.0, 0.0))) == (6, 0)   # nut, low E
    assert board_to_string_fret(1.0, 0.0) == (6, 12)                        # ref fret
    assert board_to_string_fret(-0.1, 0.5) is None                          # off board

    # End-to-end with real ArUco pixels (no camera): paint the 4 markers onto a
    # blank "board" at known corners, detect them back, map a known pixel.
    img = np.full((400, 600), 255, np.uint8)
    s = 80  # marker size px; centers at the rectangle corners below
    px_center = {0: (100, 100), 1: (500, 100), 2: (500, 300), 3: (100, 300)}
    for mid, (cx, cy) in px_center.items():
        m = cv2.aruco.generateImageMarker(_ARUCO_DICT, mid, s)
        img[cy - s // 2:cy + s // 2, cx - s // 2:cx + s // 2] = m
    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    Hd = detect_homography(img)
    assert Hd is not None, "markers not detected"
    # rectangle center pixel -> board (~0.5, ~0.5) -> string 3, fret 5
    assert board_to_string_fret(*image_to_board(Hd, (300, 200))) == (3, 5)
    print("markers_dev self-check OK (math + ArUco round-trip)")


if __name__ == "__main__":
    import sys
    _save_sheet() if "--sheet" in sys.argv else _demo()

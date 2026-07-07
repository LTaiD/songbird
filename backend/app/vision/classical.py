"""Classical-CV fretboard detector — the UNTRAINED markerless fallback.

Runs when neither trained weights nor ArUco markers are available, so a bare
guitar works out of the box. The trained keypoint detector (detector.py)
remains the accuracy path; this is Hough lines + inlay dots:

  1. Hough segments -> two angle clusters: strings (dominant total length)
     and the near-perpendicular fret wires; merge collinear fret segments;
     neck edges = the string cluster's outer envelope.
  2. Rectify each fret interval (quad between consecutive wires x edges) and
     look for inlay dots (minority-intensity blobs, contrast-agnostic).
  3. Absolute numbering NEEDS an anchor: fret spacing is self-similar (every
     gap ratio is 2^(-1/12)), so spacing alone cannot number frets — the
     12TH-FRET DOUBLE DOT is the anchor (spec §B). No double dot in frame ->
     return None and let pre-flight hint the user to include the 12th fret.

ponytail: double-dot required; single-dot chains only sanity-check direction.
Low-E edge is assumed image-top (typical facing-camera posture); the trained
detector resolves orientation properly.
"""
import math

import numpy as np
import cv2

from .fretboard import fret_u

MIN_FRETS = 5      # wires needed (>=4 intervals) to look for dots
PATCH = 48         # rectified interval size, px


def _segments(gray):
    edges = cv2.Canny(gray, 60, 160)
    w = gray.shape[1]
    segs = cv2.HoughLinesP(edges, 1, np.pi / 360, threshold=40,
                           minLineLength=w // 12, maxLineGap=8)
    return np.empty((0, 4)) if segs is None else segs.reshape(-1, 4).astype(float)


def _angle(s):
    return math.atan2(s[3] - s[1], s[2] - s[0]) % math.pi


def _cluster_angles(segs):
    """-> (string_axis_angle, string_segs, fret_segs)."""
    if len(segs) == 0:
        return None
    lengths = np.hypot(segs[:, 2] - segs[:, 0], segs[:, 3] - segs[:, 1])
    angles = np.array([_angle(s) for s in segs])
    bins = (angles / (np.pi / 18)).astype(int) % 18
    hist = np.bincount(bins, weights=lengths, minlength=18)
    win = int(np.argmax(hist))
    in_bin = bins == win
    a_str = float(np.average(angles[in_bin], weights=lengths[in_bin]))
    d = np.abs(((angles - a_str) + np.pi / 2) % np.pi - np.pi / 2)
    return a_str, segs[d < np.pi / 9], segs[np.abs(d - np.pi / 2) < np.pi / 7]


def _merge_frets(fret_segs, axis, width):
    if len(fret_segs) == 0:
        return []
    mids = (fret_segs[:, :2] + fret_segs[:, 2:]) / 2
    proj = mids @ axis
    order = np.argsort(proj)
    groups, cur = [], [order[0]]
    for i in order[1:]:
        if proj[i] - proj[cur[-1]] < width * 0.02:
            cur.append(i)
        else:
            groups.append(cur); cur = [i]
    groups.append(cur)
    out = []
    for g in groups:
        segs = fret_segs[g]
        seg = segs[int(np.argmax(np.hypot(segs[:, 2] - segs[:, 0], segs[:, 3] - segs[:, 1])))]
        out.append((float(((seg[:2] + seg[2:]) / 2) @ axis), seg))
    out.sort(key=lambda x: x[0])
    return out


def _line_through(seg):
    return np.cross([seg[0], seg[1], 1.0], [seg[2], seg[3], 1.0])


def _intersect(l1, l2):
    x = np.cross(l1, l2)
    return None if abs(x[2]) < 1e-9 else x[:2] / x[2]


def _count_dots(gray, quad):
    """Rectify an interval quad -> count inlay dots (0/1/2) in its middle."""
    dst = np.float32([(0, 0), (PATCH, 0), (PATCH, PATCH), (0, PATCH)])
    H = cv2.getPerspectiveTransform(np.float32(quad), dst)
    patch = cv2.warpPerspective(gray, H, (PATCH, PATCH))
    core = patch[6:-6, 6:-6]
    _, bw = cv2.threshold(core, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if bw.mean() > 127:          # dots are the minority intensity
        bw = 255 - bw
    n, _, stats, _ = cv2.connectedComponentsWithStats(bw, connectivity=8)
    area = core.size
    dots = 0
    for i in range(1, n):
        a, bw_, bh = stats[i, cv2.CC_STAT_AREA], stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
        if not (0.01 * area < a < 0.2 * area):
            continue
        # dots are compact; string/wire fragments are long thin strips
        # strings/wires cross the WHOLE patch; discs never do (but rectification
        # can squash them into quite long ellipses, so the bound is generous)
        if max(bw_, bh) > 0.85 * core.shape[0] or not (0.2 < bw_ / max(bh, 1) < 5.0):
            continue
        if a < 0.5 * bw_ * bh:  # low fill = not a disc
            continue
        dots += 1
    return dots


class ClassicalDetector:
    """detect(frame) -> NeckModel.fit_points correspondences | None.
    Same contract as detector.Detector.detect."""

    def detect(self, frame_bgr):
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        cl = _cluster_angles(_segments(gray))
        if cl is None:
            return None
        a_str, string_segs, fret_segs = cl
        if len(string_segs) < 2:
            return None
        axis = np.array([math.cos(a_str), math.sin(a_str)])
        normal = np.array([-axis[1], axis[0]])
        if normal[1] < 0:      # canonical: normal points image-down, so the
            normal = -normal   # min-offset edge is always the image-top edge

        offs = ((string_segs[:, :2] + string_segs[:, 2:]) / 2) @ normal
        top = _line_through(string_segs[int(np.argmin(offs))])   # low-E heuristic
        bot = _line_through(string_segs[int(np.argmax(offs))])

        wires = _merge_frets(fret_segs, axis, gray.shape[1])
        if len(wires) < MIN_FRETS:
            return None
        lines = [_line_through(seg) for _, seg in wires]
        pts = [( _intersect(l, top), _intersect(l, bot)) for l in lines]
        if any(p is None or q is None for p, q in pts):
            return None

        # interval widths shrink toward the bridge -> orient nut-first
        widths = [wires[i + 1][0] - wires[i][0] for i in range(len(wires) - 1)]
        if widths[0] < widths[-1]:
            pts, widths = pts[::-1], widths[::-1]

        # find the double-dot interval = fret space 12 (the numbering anchor)
        dots = [_count_dots(gray, (pts[i][0], pts[i + 1][0], pts[i + 1][1], pts[i][1]))
                for i in range(len(pts) - 1)]
        if dots.count(2) != 1:
            return None                       # no unambiguous 12th fret in frame
        k12 = dots.index(2)
        # wire on the bridge side of interval k = fret (space number); space k12 = 12
        first_wire_n = 12 - (k12 + 1)         # fret number of pts[0]'s wire
        if first_wire_n < 0:
            return None

        corr = []
        for i, (p_top, p_bot) in enumerate(pts):
            u = fret_u(first_wire_n + i)
            corr.append(((float(p_top[0]), float(p_top[1])), (u, 0.0)))
            corr.append(((float(p_bot[0]), float(p_bot[1])), (u, 1.0)))
        return corr


def _synthetic_neck(angle_deg=0.0, w=640, h=360):
    """Test image: strings + wires 0..13 + single dots 3/5/7/9 + double dot 12."""
    img = np.full((h, w), 235, np.uint8)
    x0, x1, y0, y1 = 40, 600, 100, 240
    span = (x1 - x0) / fret_u(13)
    wx = lambda n: x0 + span * fret_u(n)
    for i in range(6):
        y = y0 + i * (y1 - y0) / 5
        cv2.line(img, (x0 - 25, int(y)), (x1 + 10, int(y)), 60, 2)
    for n in range(14):
        cv2.line(img, (int(wx(n)), y0 - 6), (int(wx(n)), y1 + 6), 60, 2)
    ym = (y0 + y1) // 2
    for n in (3, 5, 7, 9):                    # dot sits mid-space
        cv2.circle(img, (int((wx(n - 1) + wx(n)) / 2), ym), 7, 30, -1)
    xc = int((wx(11) + wx(12)) / 2)
    for dy in (-28, 28):                      # 12th double dot
        cv2.circle(img, (xc, ym + dy), 7, 30, -1)
    if angle_deg:
        M = cv2.getRotationMatrix2D((w / 2, h / 2), angle_deg, 1.0)
        img = cv2.warpAffine(img, M, (w, h), borderValue=235)
        pt = lambda x, y: tuple((M @ np.array([x, y, 1.0])).tolist())
    else:
        pt = lambda x, y: (float(x), float(y))
    return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR), pt, wx, y0, y1


def _demo():
    from .fretboard import NeckModel
    for ang in (0.0, 8.0):
        frame, pt, wx, y0, y1 = _synthetic_neck(angle_deg=ang)
        corr = ClassicalDetector().detect(frame)
        assert corr, f"no detection at {ang} deg"
        m = NeckModel()
        assert m.fit_points(corr)
        # fingertip just behind fret 7, on string 2 (v=0.8)
        sf = m.image_to_string_fret(pt(wx(7) - 4, y0 + 0.8 * (y1 - y0)))
        assert sf == (2, 7), f"{ang} deg -> {sf}"
        assert m.image_to_string_fret(pt(wx(0) + 2, y0 + 2))[1] == 0  # open @ nut
    # degeneracy guard: without the double dot there is NO absolute anchor
    frame, *_ = _synthetic_neck()
    g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    ym = (100 + 240) // 2
    from .fretboard import fret_u as fu
    span = (600 - 40) / fu(13)
    xc = int(40 + span * (fu(11) + fu(12)) / 2)
    cv2.circle(g, (xc, ym - 28), 9, 235, -1); cv2.circle(g, (xc, ym + 28), 9, 235, -1)
    assert ClassicalDetector().detect(cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)) is None
    print("classical self-check OK (dot-anchored numbering, 0deg & 8deg + no-anchor guard)")


if __name__ == "__main__":
    _demo()

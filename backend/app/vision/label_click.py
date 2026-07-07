"""Click-labeler for BARE (marker-free) photos — the manual fallback.

For each image: click, in order —
  1. nut at the low-E edge      2. nut at the high-E edge
  3..7. inlay dots for frets 3, 5, 7, 9, 12 (the double-dot; click between them)
Keys: u = undo last click, s = skip image, q = quit. Auto-advances when done.

Run: python -m backend.app.vision.label_click <photo_dir> <out_dir>
Output matches label_from_markers.py ({nut, inlays, dot12} JSON per image).
"""
import os
import sys
import json

import cv2

ORDER = ["nut low-E", "nut high-E", "inlay 3", "inlay 5", "inlay 7", "inlay 9", "inlay 12"]


def label_image(img, name):
    pts = []
    win = f"label: {name}"

    def on_click(ev, x, y, *_):
        if ev == cv2.EVENT_LBUTTONDOWN and len(pts) < len(ORDER):
            pts.append((float(x), float(y)))

    cv2.namedWindow(win)
    cv2.setMouseCallback(win, on_click)
    while True:
        disp = img.copy()
        for i, p in enumerate(pts):
            cv2.circle(disp, (int(p[0]), int(p[1])), 4, (0, 255, 0), -1)
            cv2.putText(disp, ORDER[i], (int(p[0]) + 6, int(p[1]) - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        nxt = ORDER[len(pts)] if len(pts) < len(ORDER) else "done"
        cv2.putText(disp, f"click: {nxt}  (u=undo s=skip q=quit)", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.imshow(win, disp)
        k = cv2.waitKey(30) & 0xFF
        if k == ord("u") and pts:
            pts.pop()
        elif k == ord("s"):
            cv2.destroyWindow(win)
            return None
        elif k == ord("q"):
            cv2.destroyWindow(win)
            return "quit"
        elif len(pts) == len(ORDER):
            cv2.destroyWindow(win)
            inlays = {n: list(p) for n, p in zip(["3", "5", "7", "9", "12"], pts[2:])}
            return {"nut": [list(pts[0]), list(pts[1])], "inlays": inlays,
                    "dot12": inlays["12"]}


def main(src, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    saved = 0
    for f in sorted(os.listdir(src)):
        if not f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
            continue
        img = cv2.imread(os.path.join(src, f))
        if img is None:
            continue
        kp = label_image(img, f)
        if kp == "quit":
            break
        if kp:
            base = os.path.join(out_dir, os.path.splitext(f)[0])
            cv2.imwrite(base + ".png", img)
            json.dump(kp, open(base + ".json", "w"))
            saved += 1
    print(f"labeled {saved} images -> {out_dir}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])

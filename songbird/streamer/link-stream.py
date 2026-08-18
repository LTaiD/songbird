#!/usr/bin/env python3

import html
import json
import os
import random
import sys

from PySide6 import QtCore, QtGui, QtWidgets

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from engine import Engine, fmt_time, SEEK_STEP_MS, SEEK_REPEAT_MS  # noqa: E402
from songbird.links import links as resolve_links  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
WORKER = os.path.join(_HERE, "identify_worker.py")
LOOP_ICON = os.path.join(_REPO, "assets", "loop.jpg")
IDENTIFY_CONFIG = "full"
MATCH_TIMEOUT_MS = 180000


SNOW = "#FFFAFA"
INK = "#141414"
LIGHTBLUE = "#A6CFEA"
NAVY = "#2C3A8C"
GREEN = "#9CC93B"
LIGHTGREY = "#CAD3DA"
INSEC = "#6E86C0"
MUTED = "#8A8A8A"

SUBTITLE = "identify song names from live-instrument recordings"

TIMELINE_HEIGHT = 46
HEADER_HEIGHT = 158


FONT_FAMILY = "Helvetica Neue"


def hn(size, weight=QtGui.QFont.Weight.Medium, spacing=0.0, upper_tracking=False):
    f = QtGui.QFont(FONT_FAMILY)
    f.setPixelSize(size)
    f.setWeight(weight)
    if spacing:
        f.setLetterSpacing(QtGui.QFont.SpacingType.AbsoluteSpacing, spacing)
    return f


BLACK = QtGui.QFont.Weight.Bold
MEDIUM = QtGui.QFont.Weight.Medium
LIGHT = QtGui.QFont.Weight.Light


class HeaderBand(QtWidgets.QWidget):

    FLOCK = [
        (0.46, 0.24, 40, 24, 0.44, 0.08), (0.55, 0.62, 30, 20, 0.08, 0.46),
        (0.64, 0.28, 46, 28, 0.46, 0.10), (0.72, 0.68, 32, 20, 0.10, 0.44),
        (0.80, 0.22, 36, 24, 0.44, 0.08), (0.87, 0.54, 42, 26, 0.12, 0.46),
        (0.93, 0.30, 30, 18, 0.42, 0.10), (0.98, 0.66, 26, 16, 0.10, 0.42),
    ]

    def __init__(self):
        super().__init__()
        self.setFixedHeight(HEADER_HEIGHT)

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, False)
        w, h = self.width(), self.height()
        p.fillRect(self.rect(), QtGui.QColor(SNOW))

        p.fillRect(0, 2, 24, h - 4, QtGui.QColor(LIGHTBLUE))

        wx = 42
        wf = hn(40, BLACK, spacing=1.0)
        p.setFont(wf)
        p.setPen(QtGui.QColor(INK))
        p.drawText(QtCore.QRect(wx, 2, w - wx, 52),
                   QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, "songbird")
        ww = QtGui.QFontMetrics(wf).horizontalAdvance("songbird")
        p.setFont(hn(15, LIGHT))
        p.setPen(QtGui.QColor(GREEN))
        p.drawText(QtCore.QRect(wx + ww + 16, 4, w - (wx + ww + 16), 52),
                   QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, SUBTITLE)

        self._squares(p, wx, 60, w - wx - 4, h - 62)

    def _gull_segs(self, cx, cy, half, ht, shoulder, tip):
        sh, tp, body = shoulder * ht, tip * ht, 0.10 * ht
        knots = [(-1.0, tp), (-0.42, sh), (0.0, body), (0.42, sh), (1.0, tp)]
        pts = [(cx + u * half, cy - v) for u, v in knots]
        return list(zip(pts, pts[1:]))

    @staticmethod
    def _pt_seg_dist2(px, py, a, b):
        ax, ay = a
        bx, by = b
        dx, dy = bx - ax, by - ay
        d2 = dx * dx + dy * dy
        t = 0.0 if d2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / d2))
        qx, qy = ax + t * dx, ay + t * dy
        return (px - qx) ** 2 + (py - qy) ** 2

    def _squares(self, p, x0, y0, fw, fh):
        rng = random.Random(7)
        cell, sq = 7, 5
        wing2 = 5.5 ** 2
        cols = max(1, fw // cell)
        rows = max(1, fh // cell)
        gulls = [self._gull_segs(x0 + fx * fw, y0 + fy * fh, half, ht, sh, tp)
                 for fx, fy, half, ht, sh, tp in self.FLOCK]
        for r in range(rows):
            for c in range(cols):
                gx = x0 + c * cell
                gy = y0 + r * cell
                cx, cy = gx + cell / 2, gy + cell / 2
                on_gull = any(self._pt_seg_dist2(cx, cy, a, b) <= wing2
                              for segs in gulls for a, b in segs)
                if on_gull:
                    col = LIGHTBLUE if rng.random() < 0.14 else NAVY
                    p.setPen(QtGui.QPen(QtGui.QColor(col), 1))
                    p.setBrush(QtGui.QColor(col))
                    p.drawRect(int(gx), int(gy), sq, sq)
                    continue

                frac = c / max(1, cols - 1)
                keep = max(0.02, (1.0 - frac) ** 1.9) * 0.45
                if rng.random() < keep:
                    col = rng.choice([LIGHTBLUE, NAVY, GREEN])
                    jx, jy = rng.randint(-2, 2), rng.randint(-2, 2)
                    if rng.random() < 0.35:
                        p.setPen(QtGui.QPen(QtGui.QColor(col), 1))
                        p.setBrush(QtGui.QColor(col))
                    else:
                        p.setPen(QtGui.QPen(QtGui.QColor(col), 2))
                        p.setBrush(QtCore.Qt.NoBrush)
                    p.drawRect(int(gx + jx), int(gy + jy), sq, sq)


class Timeline(QtWidgets.QWidget):

    seekRequested = QtCore.Signal(float)
    sectionChanged = QtCore.Signal(object, object)
    scrubbing = QtCore.Signal(bool)

    HANDLE_PX = 6

    def __init__(self):
        super().__init__()
        self.setFixedHeight(TIMELINE_HEIGHT)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setMouseTracking(True)
        self.position = 0.0
        self.sec_a = None
        self.sec_b = None
        self.seeking = False
        self._pending_first = None
        self._drag_handle = None
        self.peaks = None

    def set_position(self, frac):
        self.position = min(1.0, max(0.0, frac))
        self.update()

    def set_peaks(self, peaks):
        self.peaks = peaks
        self.update()

    def apply_section(self, a, b):
        self.sec_a, self.sec_b, self._pending_first = a, b, None
        self.update()

    def _frac(self, x):
        return min(1.0, max(0.0, x / max(1, self.width())))

    def _handle_at(self, x):
        if self.sec_a is None or self.sec_b is None:
            return None
        w = max(1, self.width())
        if abs(x - self.sec_a * w) <= self.HANDLE_PX:
            return "a"
        if abs(x - self.sec_b * w) <= self.HANDLE_PX:
            return "b"
        return None

    def mousePressEvent(self, e):
        if e.button() != QtCore.Qt.LeftButton:
            return
        x = e.position().x()
        f = self._frac(x)
        if e.modifiers() & QtCore.Qt.ShiftModifier:
            if self._pending_first is None:
                self._pending_first = f
                self.sec_a = self.sec_b = None
            else:
                self.sec_a = min(self._pending_first, f)
                self.sec_b = max(self._pending_first, f)
                self._pending_first = None
            self.update()
            self.sectionChanged.emit(self.sec_a, self.sec_b)
            return
        handle = self._handle_at(x)
        if handle is not None:
            self._drag_handle = handle
            return
        self.seeking = True
        self.scrubbing.emit(True)
        self.position = f
        self.seekRequested.emit(self.position)
        self.update()

    def mouseMoveEvent(self, e):
        x = e.position().x()
        if self._drag_handle is not None and (e.buttons() & QtCore.Qt.LeftButton):
            f = self._frac(x)
            if self._drag_handle == "a":
                self.sec_a = min(f, self.sec_b)
            else:
                self.sec_b = max(f, self.sec_a)
            self.update()
            self.sectionChanged.emit(self.sec_a, self.sec_b)
        elif self.seeking and (e.buttons() & QtCore.Qt.LeftButton):
            self.position = self._frac(x)
            self.seekRequested.emit(self.position)
            self.update()
        else:
            on_handle = self._handle_at(x) is not None
            self.setCursor(QtCore.Qt.SizeHorCursor if on_handle
                           else QtCore.Qt.PointingHandCursor)

    def mouseReleaseEvent(self, e):
        if e.button() == QtCore.Qt.LeftButton:
            if self.seeking:
                self.seeking = False
                self.scrubbing.emit(False)
            self._drag_handle = None

    def mouseDoubleClickEvent(self, e):
        self.sec_a = self.sec_b = self._pending_first = None
        self.update()
        self.sectionChanged.emit(None, None)

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        w, h = self.width(), self.height()
        mid = h // 2
        p.fillRect(self.rect(), QtGui.QColor(SNOW))
        pos_x = self.position * w
        has_sec = self.sec_a is not None and self.sec_b is not None
        xa = self.sec_a * w if has_sec else 0.0
        xb = self.sec_b * w if has_sec else 0.0

        if has_sec:
            p.fillRect(int(xa), 0, max(1, int(xb - xa)), h, QtGui.QColor(LIGHTBLUE))

        if self.peaks is not None and len(self.peaks) and w > 0:
            n = len(self.peaks)
            half = h / 2 - 3
            grey = QtGui.QColor(LIGHTGREY)
            insec = QtGui.QColor(INSEC)
            ink = QtGui.QColor(INK)
            for x in range(w):
                amp = float(self.peaks[int(x / w * n)])
                bar = max(1.0, amp * half)
                played = x <= pos_x
                if has_sec and xa <= x <= xb:
                    color = ink if played else insec
                else:
                    color = ink if played else grey
                p.setPen(color)
                p.drawLine(x, int(mid - bar), x, int(mid + bar))
        else:
            p.setPen(QtGui.QPen(QtGui.QColor(LIGHTGREY), 2))
            p.drawLine(0, mid, w, mid)

        if has_sec:
            p.fillRect(int(xa) - 1, 0, 3, h, QtGui.QColor(NAVY))
            p.fillRect(int(xb) - 1, 0, 3, h, QtGui.QColor(NAVY))
        elif self._pending_first is not None:
            p.fillRect(int(self._pending_first * w) - 1, 0, 3, h, QtGui.QColor(NAVY))

        x = int(pos_x)
        p.setPen(QtGui.QPen(QtGui.QColor(NAVY), 2))
        p.drawLine(x, 0, x, h)


class VideoContainer(QtWidgets.QWidget):
    resized = QtCore.Signal()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.resized.emit()


class VideoFrame(QtWidgets.QFrame):
    clicked = QtCore.Signal()
    wheelZoom = QtCore.Signal(float, QtCore.QPointF)
    pinchZoom = QtCore.Signal(float, QtCore.QPointF)

    def mousePressEvent(self, e):
        if e.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(e)

    def wheelEvent(self, e):
        if e.modifiers() & QtCore.Qt.ControlModifier:
            self.wheelZoom.emit(float(e.angleDelta().y()), e.globalPosition())
            e.accept()
        else:
            super().wheelEvent(e)

    def event(self, e):
        if e.type() == QtCore.QEvent.Type.NativeGesture and \
                e.gestureType() == QtCore.Qt.NativeGestureType.ZoomNativeGesture:
            self.pinchZoom.emit(float(e.value()), e.globalPosition())
            return True
        return super().event(e)


class Window(QtWidgets.QWidget):
    ZOOM_MIN = 1.0
    ZOOM_MAX = 8.0

    _matchDone = QtCore.Signal(object)
    _matchFailed = QtCore.Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("songbird live-music finder")
        self.resize(960, 700)
        self.setStyleSheet(f"background:{SNOW}; color:{INK};")

        self.engine = Engine()
        self._zoom = 1.0
        self._nx = self._ny = 0.5
        self._pre_mute_volume = 100
        self._matching = False
        self._proc = None
        self._proc_buf = ""
        self._match_timer = QtCore.QTimer(self)
        self._match_timer.setSingleShot(True)
        self._match_timer.setInterval(MATCH_TIMEOUT_MS)
        self._match_timer.timeout.connect(self._on_match_timeout)

        self._build_ui()

        self.engine.tick.connect(self._on_tick)
        self.engine.waveform.connect(self.timeline.set_peaks)
        self.engine.section_changed.connect(self.timeline.apply_section)
        self.engine.status.connect(self._on_status)
        self.engine.loaded.connect(self._on_loaded)
        self.engine.playing_changed.connect(self._on_playing)
        self.timeline.seekRequested.connect(self.engine.seek_fraction)
        self.timeline.sectionChanged.connect(self.engine.set_section)
        self.timeline.scrubbing.connect(self.engine.set_scrubbing)
        self._matchDone.connect(self._on_match_done)
        self._matchFailed.connect(self._on_match_failed)

        self._seek_dir = 0
        self._seek_timer = QtCore.QTimer(self)
        self._seek_timer.setInterval(SEEK_REPEAT_MS)
        self._seek_timer.timeout.connect(
            lambda: self.engine.seek_relative(self._seek_dir * SEEK_STEP_MS))
        QtWidgets.QApplication.instance().installEventFilter(self)

    def _flat_button(self, text, on_click):
        b = QtWidgets.QPushButton(text)
        b.setFont(hn(13, MEDIUM))
        b.setCursor(QtCore.Qt.PointingHandCursor)
        b.setStyleSheet(
            f"QPushButton{{background:transparent; color:{INK}; border:none;"
            f" padding:6px 10px;}}"
            f"QPushButton:hover{{color:{NAVY};}}"
            f"QPushButton:disabled{{color:{LIGHTGREY};}}")
        b.clicked.connect(on_click)
        return b

    def _label(self, text, weight=MEDIUM, size=12, color=INK):
        lab = QtWidgets.QLabel(text)
        lab.setFont(hn(size, weight, spacing=1.0 if weight == MEDIUM else 0.0))
        lab.setStyleSheet(f"color:{color};")
        return lab

    def _value_edit(self, text, width, on_commit):
        e = QtWidgets.QLineEdit(text)
        e.setFont(hn(12, LIGHT))
        e.setFixedWidth(width)
        e.setAlignment(QtCore.Qt.AlignLeft)
        e.setStyleSheet(
            f"QLineEdit{{background:transparent; color:{INK}; border:none;"
            f" border-bottom:1px solid {LIGHTGREY}; padding:1px 0;}}"
            f"QLineEdit:focus{{border-bottom:1px solid {NAVY};}}")
        e.editingFinished.connect(on_commit)
        return e

    def _loop_toggle(self):
        b = QtWidgets.QPushButton("LOOP")
        b.setCheckable(True)
        b.setCursor(QtCore.Qt.PointingHandCursor)
        b.setToolTip("loop autoplay: repeat the whole track when it ends")
        icon = QtGui.QIcon(LOOP_ICON)
        if not icon.isNull():
            b.setIcon(icon)
            b.setIconSize(QtCore.QSize(16, 16))
        b.setFont(hn(13, MEDIUM))
        b.setStyleSheet(
            f"QPushButton{{background:transparent; color:{MUTED}; border:none;"
            f" padding:6px 10px;}}"
            f"QPushButton:hover{{color:{NAVY};}}"
            f"QPushButton:checked{{color:{NAVY}; border-bottom:2px solid {NAVY};}}")
        b.toggled.connect(self.engine.set_loop)
        return b

    def _slider(self, lo, hi, val, width, handle_color):
        s = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        s.setMinimum(lo)
        s.setMaximum(hi)
        s.setValue(val)
        s.setFixedWidth(width)
        s.setStyleSheet(
            f"QSlider::groove:horizontal{{height:2px; background:{INK};}}"
            f"QSlider::sub-page:horizontal{{height:2px; background:{INK};}}"
            f"QSlider::handle:horizontal{{width:12px; height:12px; margin:-6px 0;"
            f" background:{handle_color}; border:none;}}")
        return s

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 14)
        root.setSpacing(12)

        root.addWidget(HeaderBand())

        top = QtWidgets.QHBoxLayout()
        top.setSpacing(14)
        self.url_edit = QtWidgets.QLineEdit()
        self.url_edit.setFont(hn(15, LIGHT))
        self.url_edit.setPlaceholderText("paste YouTube or TikTok link")
        self.url_edit.setStyleSheet(
            f"QLineEdit{{background:transparent; color:{INK}; border:none;"
            f" border-bottom:1px solid {INK}; padding:6px 0;}}")
        self.url_edit.returnPressed.connect(self._load)
        top.addWidget(self.url_edit, 1)
        top.addWidget(self._flat_button("LOAD", self._load))
        self.upload_btn = self._flat_button("FILE UPLOAD", self.match_file)
        self.identify_btn = self._flat_button("IDENTIFY SONG", self.match_loaded)
        self.identify_btn.setEnabled(False)
        top.addWidget(self.upload_btn)
        top.addWidget(self.identify_btn)
        root.addLayout(top)

        self.video_container = VideoContainer()
        self.video_container.setStyleSheet(
            f"background:black; border:2px solid {NAVY};")
        self.video_container.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                           QtWidgets.QSizePolicy.Expanding)
        self.video_container.resized.connect(lambda: self._apply_video_geometry(None))

        self.videoframe = VideoFrame(self.video_container)
        self.videoframe.setStyleSheet("background:black; border:none;")
        self.videoframe.setAttribute(QtCore.Qt.WA_NativeWindow, True)
        self.videoframe.clicked.connect(self.engine.play_pause)
        self.videoframe.wheelZoom.connect(self._on_wheel_zoom)
        self.videoframe.pinchZoom.connect(self._on_pinch_zoom)

        root.addWidget(self.video_container, 1)

        self.timeline = Timeline()
        root.addWidget(self.timeline)

        ctl = QtWidgets.QHBoxLayout()
        ctl.setSpacing(14)
        self.play_btn = self._flat_button("PLAY", self.engine.play_pause)
        self.play_btn.setFixedWidth(74)
        ctl.addWidget(self.play_btn)
        self.loop_btn = self._loop_toggle()
        ctl.addWidget(self.loop_btn)
        self.time_lbl = self._label("0:00 / 0:00", MEDIUM, 13)
        ctl.addWidget(self.time_lbl)
        ctl.addSpacing(10)

        ctl.addWidget(self._label("SPEED", MEDIUM, 11, MUTED))
        self.speed = self._slider(25, 200, 100, 130, NAVY)
        self.speed.valueChanged.connect(self._on_speed)
        ctl.addWidget(self.speed)
        self.speed_edit = self._value_edit("1.00x", 46, self._commit_speed)
        ctl.addWidget(self.speed_edit)
        ctl.addSpacing(10)

        ctl.addWidget(self._label("VOL", MEDIUM, 11, MUTED))
        self.volume = self._slider(0, 100, 100, 110, GREEN)
        self.volume.valueChanged.connect(self._on_volume)
        ctl.addWidget(self.volume)
        self.volume_edit = self._value_edit("100%", 40, self._commit_volume)
        ctl.addWidget(self.volume_edit)
        ctl.addStretch(1)
        root.addLayout(ctl)

        self.status = QtWidgets.QLineEdit("no song loaded")
        self.status.setReadOnly(True)
        self.status.setFont(hn(12, LIGHT))
        self.status.setStyleSheet(
            f"background:transparent; color:{MUTED}; border:none;")
        root.addWidget(self.status)

        self.result = QtWidgets.QLabel("")
        self.result.setFont(hn(14, LIGHT))
        self.result.setTextFormat(QtCore.Qt.RichText)
        self.result.setOpenExternalLinks(True)
        self.result.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        self.result.setWordWrap(True)
        self.result.setStyleSheet(
            f"background:{LIGHTBLUE}; color:{INK}; padding:10px;")
        self.result.setVisible(False)
        root.addWidget(self.result)

    def _on_tick(self, frac, ms, length):
        if not self.timeline.seeking:
            self.timeline.set_position(frac)
        self.time_lbl.setText(f"{fmt_time(ms)} / {fmt_time(length)}")
        if self.engine.is_playing() and self.url_edit.hasFocus():
            self.url_edit.clearFocus()

    def _on_status(self, msg):
        self.status.setText(str(msg))
        self.status.setCursorPosition(0)

    def _on_loaded(self, title):
        self.setWindowTitle(
            f"songbird live-music finder — {title}" if title
            else "songbird live-music finder")
        self._zoom = 1.0
        self._nx = self._ny = 0.5
        self._apply_video_geometry(None)
        self.url_edit.clearFocus()
        self.identify_btn.setEnabled(bool(self.engine.match_source()) and not self._matching)

    def _on_playing(self, playing):
        self.play_btn.setText("PAUSE" if playing else "PLAY")

    def _load(self):
        self.engine.load(self.url_edit.text())

    def match_file(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Choose a recording", "",
            "Audio/Video (*.mp3 *.wav *.m4a *.flac *.ogg *.mp4 *.mov *.mkv *.webm)")
        if path:
            self._start_match(path, is_url=False)

    def match_loaded(self):
        src = self.engine.match_source()
        if src:
            self._start_match(src, is_url=True)

    def _ensure_worker(self):
        if self._proc is not None and self._proc.state() != QtCore.QProcess.NotRunning:
            return
        self._proc_buf = ""
        proc = QtCore.QProcess(self)
        proc.setProgram(sys.executable)
        proc.setArguments([WORKER])
        proc.readyReadStandardOutput.connect(self._on_worker_out)
        proc.finished.connect(self._on_worker_finished)
        proc.start()
        self._proc = proc

    def _start_match(self, src, is_url):
        if self._matching:
            return
        self._matching = True
        self.upload_btn.setEnabled(False)
        self.identify_btn.setEnabled(False)
        self.result.setVisible(False)
        self._on_status("identifying song… (CPU, this can take a minute)")
        try:
            self._ensure_worker()
            req = json.dumps({"src": src, "is_url": bool(is_url),
                              "config": IDENTIFY_CONFIG}) + "\n"
            self._proc.write(req.encode("utf-8"))
        except Exception as exc:
            self._matchFailed.emit(f"could not start matcher: {exc}")
            return
        self._match_timer.start()

    def _on_worker_out(self):
        if self._proc is None:
            return
        self._proc_buf += bytes(self._proc.readAllStandardOutput()).decode("utf-8", "replace")
        while "\n" in self._proc_buf:
            line, self._proc_buf = self._proc_buf.split("\n", 1)
            line = line.strip()
            if not line:
                continue
            try:
                res = json.loads(line)
            except Exception:
                continue
            if not isinstance(res, dict) or "ok" not in res:
                continue
            self._match_timer.stop()
            if res.get("ok"):
                song = res.get("song")
                pred = (song, res.get("artist"), res.get("apple_url") or "") if song else None
                self._matchDone.emit(pred)
            else:
                self._matchFailed.emit(f"match error: {res.get('error', 'unknown')}")

    def _on_worker_finished(self, _code, _status):
        self._proc = None
        if self._matching:
            self._match_timer.stop()
            self._matchFailed.emit("matcher crashed — please try again")

    def _on_match_timeout(self):
        if self._proc is not None:
            self._proc.kill()
            self._proc = None
        if self._matching:
            self._matchFailed.emit("match timed out")

    def _on_match_done(self, pred):
        self._matching = False
        self.upload_btn.setEnabled(True)
        self.identify_btn.setEnabled(bool(self.engine.match_source()))
        if not pred:
            self._on_status("no match: reference index is empty or unreadable")
            return
        song, artist, apple_url = pred
        apple, spotify, tiktok = resolve_links(song, artist, apple_url)
        self.result.setText(
            f"<b>{html.escape(song)}</b><br>{html.escape(artist)}<br>"
            f'<a style="color:{NAVY}" href="{html.escape(apple)}">Apple Music</a>'
            f' &nbsp; <a style="color:{NAVY}" href="{html.escape(spotify)}">Spotify</a>'
            f' &nbsp; <a style="color:{NAVY}" href="{html.escape(tiktok)}">TikTok</a>')
        self.result.setVisible(True)
        self._on_status("done")

    def _on_match_failed(self, msg):
        self._matching = False
        self.upload_btn.setEnabled(True)
        self.identify_btn.setEnabled(bool(self.engine.match_source()))
        self._on_status(msg)

    def _on_speed(self, value):
        rate = value / 100.0
        self.engine.set_speed(rate)
        if not self.speed_edit.hasFocus():
            self.speed_edit.setText(f"{rate:.2f}x")

    def _on_volume(self, value):
        self.engine.set_volume(int(value))
        if not self.volume_edit.hasFocus():
            self.volume_edit.setText(f"{int(value)}%")

    def _commit_speed(self):
        try:
            rate = float(self.speed_edit.text().lower().replace("x", "").strip())
        except ValueError:
            rate = self.speed.value() / 100.0
        self.speed.setValue(max(25, min(200, int(round(rate * 100)))))
        self.speed_edit.setText(f"{self.speed.value() / 100.0:.2f}x")

    def _commit_volume(self):
        try:
            vol = int(float(self.volume_edit.text().replace("%", "").strip()))
        except ValueError:
            vol = self.volume.value()
        self.volume.setValue(max(0, min(100, vol)))
        self.volume_edit.setText(f"{self.volume.value()}%")

    def _toggle_mute(self):
        if self.volume.value() > 0:
            self._pre_mute_volume = self.volume.value()
            self.volume.setValue(0)
        else:
            self.volume.setValue(self._pre_mute_volume or 100)

    def _apply_video_geometry(self, focal):
        W = self.video_container.width()
        H = self.video_container.height()
        if W <= 0 or H <= 0:
            return
        fw = W * self._zoom
        fh = H * self._zoom
        if focal is not None and fw > W:
            g = self.videoframe.geometry()
            ow = g.width() or W
            oh = g.height() or H
            cfx = (focal.x() - g.x()) / ow
            cfy = (focal.y() - g.y()) / oh
            ox = focal.x() - cfx * fw
            oy = focal.y() - cfy * fh
        else:
            ox = -self._nx * (fw - W)
            oy = -self._ny * (fh - H)
        ox = min(0.0, max(W - fw, ox))
        oy = min(0.0, max(H - fh, oy))
        self.videoframe.setGeometry(round(ox), round(oy), round(fw), round(fh))
        if fw > W:
            self._nx = -ox / (fw - W)
        if fh > H:
            self._ny = -oy / (fh - H)

    def _zoom_by(self, factor, global_pos):
        new = max(self.ZOOM_MIN, min(self.ZOOM_MAX, self._zoom * factor))
        if abs(new - self._zoom) < 1e-4:
            return
        self._zoom = new
        focal = self.video_container.mapFromGlobal(global_pos.toPoint())
        self._apply_video_geometry(QtCore.QPointF(focal))

    def _on_wheel_zoom(self, angle_delta, global_pos):
        self._zoom_by(1.0 + 0.0015 * angle_delta, global_pos)

    def _on_pinch_zoom(self, value, global_pos):
        self._zoom_by(1.0 + value, global_pos)

    def eventFilter(self, obj, event):
        et = event.type()
        typing = isinstance(QtWidgets.QApplication.focusWidget(),
                            QtWidgets.QLineEdit)
        if et in (QtCore.QEvent.KeyPress, QtCore.QEvent.KeyRelease) and not typing:
            key = event.key()
            if key in (QtCore.Qt.Key_Left, QtCore.Qt.Key_Right):
                if event.isAutoRepeat():
                    return True
                if et == QtCore.QEvent.KeyPress:
                    self._seek_dir = -1 if key == QtCore.Qt.Key_Left else 1
                    self.engine.seek_relative(self._seek_dir * SEEK_STEP_MS)
                    self._seek_timer.start()
                else:
                    self._seek_timer.stop()
                return True
            if key == QtCore.Qt.Key_Space:
                if et == QtCore.QEvent.KeyPress and not event.isAutoRepeat():
                    self.engine.play_pause()
                return True
            if key == QtCore.Qt.Key_M:
                if et == QtCore.QEvent.KeyPress and not event.isAutoRepeat():
                    self._toggle_mute()
                return True
            if key in (QtCore.Qt.Key_Up, QtCore.Qt.Key_Down):
                if et == QtCore.QEvent.KeyPress:
                    step = 5 if key == QtCore.Qt.Key_Up else -5
                    self.volume.setValue(self.volume.value() + step)
                return True
        return super().eventFilter(obj, event)

    def closeEvent(self, e):
        if self._proc is not None:
            self._proc.kill()
        self.engine.close()
        super().closeEvent(e)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = Window()
    win.show()
    win.engine.attach_video(int(win.videoframe.winId()))
    sys.exit(app.exec())

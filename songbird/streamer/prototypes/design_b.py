#!/usr/bin/env python3
"""
design_b — Swiss / Blue Note "color-block band" UI for Songbird Archive Streamer.

Minimalist, geometric, Reid-Miles album-cover feel: warm cream ground, big
Helvetica Neue header in a color-block band, Promise-Ring primaries, flat type.
All playback plumbing comes from engine.py — this file is pure look & layout.

Run:  cd songbird-archive-streamer && .venv/bin/python prototypes/design_b.py
"""

import os
import random
import sys

from PySide6 import QtCore, QtGui, QtWidgets

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine import Engine, fmt_time, SEEK_STEP_MS, SEEK_REPEAT_MS  # noqa: E402

# ---- palette (snow white + Joan-of-Arc light blue / navy / green) ----
SNOW = "#FFFAFA"
INK = "#141414"
LIGHTBLUE = "#A6CFEA"
NAVY = "#2C3A8C"
GREEN = "#9CC93B"
LIGHTGREY = "#CAD3DA"   # unplayed waveform
INSEC = "#6E86C0"       # unplayed waveform inside the (light-blue) section
MUTED = "#8A8A8A"

SUBTITLE = "loop any section of a youtube link"

TIMELINE_HEIGHT = 46
HEADER_HEIGHT = 128

# ---- type: all Helvetica Neue, routed through one helper so a bundled,
# redistributable face can be swapped in later (addApplicationFont) ----
FONT_FAMILY = "Helvetica Neue"


def hn(size, weight=QtGui.QFont.Weight.Medium, spacing=0.0, upper_tracking=False):
    f = QtGui.QFont(FONT_FAMILY)
    f.setPixelSize(size)
    f.setWeight(weight)
    if spacing:
        f.setLetterSpacing(QtGui.QFont.SpacingType.AbsoluteSpacing, spacing)
    return f


BLACK = QtGui.QFont.Weight.Bold      # heaviest installed regular-width face
MEDIUM = QtGui.QFont.Weight.Medium
LIGHT = QtGui.QFont.Weight.Light


class HeaderBand(QtWidgets.QWidget):
    """Joan-of-Arc treatment: a tall thin light-blue block, the wordmark
    with a green subtitle, and a dense->sparse field of hollow outlined squares
    (light blue / navy / green) dispersing to the right."""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(HEADER_HEIGHT)

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, False)
        w, h = self.width(), self.height()
        p.fillRect(self.rect(), QtGui.QColor(SNOW))

        # tall thin light-blue color-field block on the far left
        p.fillRect(0, 2, 24, h - 4, QtGui.QColor(LIGHTBLUE))

        # wordmark + baseline-aligned green subtitle
        wx = 42
        wf = hn(40, BLACK, spacing=1.0)
        p.setFont(wf)
        p.setPen(QtGui.QColor(INK))
        p.drawText(QtCore.QRect(wx, 2, w - wx, 52),
                   QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, "SONGBIRD ARCHIVE STREAMER")
        ww = QtGui.QFontMetrics(wf).horizontalAdvance("SONGBIRD ARCHIVE STREAMER")
        p.setFont(hn(15, LIGHT))
        p.setPen(QtGui.QColor(GREEN))
        p.drawText(QtCore.QRect(wx + ww + 16, 4, w - (wx + ww + 16), 52),
                   QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, SUBTITLE)

        # scattering hollow-square field below the wordmark
        self._squares(p, wx, 60, w - wx - 4, h - 62)

    def _squares(self, p, x0, y0, fw, fh):
        rng = random.Random(7)              # fixed seed -> stable layout
        cell, sq = 18, 12
        cols = max(1, fw // cell)
        rows = max(1, fh // cell)
        p.setBrush(QtCore.Qt.NoBrush)
        for r in range(rows):
            for c in range(cols):
                fx = c / max(1, cols - 1)
                keep = max(0.05, (1.0 - fx) ** 1.7)   # dense left, sparse right
                if rng.random() < keep:
                    col = rng.choice([LIGHTBLUE, NAVY, GREEN])
                    jx = rng.randint(-2, 2)
                    jy = rng.randint(-2, 2)
                    p.setPen(QtGui.QPen(QtGui.QColor(col), 2))
                    p.drawRect(int(x0 + c * cell + jx),
                               int(y0 + r * cell + jy), sq, sq)


class Timeline(QtWidgets.QWidget):
    """Seek bar: waveform + playhead + Shift+click A-B section with edge handles.
    Same interaction as the baseline; restyled to the cream/primaries palette."""

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

        # section: solid light-blue block behind the bars
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

        # section edge handles (navy) / pending first-edge line
        if has_sec:
            p.fillRect(int(xa) - 1, 0, 3, h, QtGui.QColor(NAVY))
            p.fillRect(int(xb) - 1, 0, 3, h, QtGui.QColor(NAVY))
        elif self._pending_first is not None:
            p.fillRect(int(self._pending_first * w) - 1, 0, 3, h, QtGui.QColor(NAVY))

        # playhead: navy
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

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Songbird Archive Streamer — design_b")
        self.resize(960, 700)
        self.setStyleSheet(f"background:{SNOW}; color:{INK};")

        self.engine = Engine()
        self._zoom = 1.0
        self._nx = self._ny = 0.5
        self._pre_mute_volume = 100

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

        self._seek_dir = 0
        self._seek_timer = QtCore.QTimer(self)
        self._seek_timer.setInterval(SEEK_REPEAT_MS)
        self._seek_timer.timeout.connect(
            lambda: self.engine.seek_relative(self._seek_dir * SEEK_STEP_MS))
        QtWidgets.QApplication.instance().installEventFilter(self)

    # ---- layout (the design surface) ----
    def _flat_button(self, text, on_click):
        b = QtWidgets.QPushButton(text)
        b.setFont(hn(13, MEDIUM))
        b.setCursor(QtCore.Qt.PointingHandCursor)
        b.setStyleSheet(
            f"QPushButton{{background:transparent; color:{INK}; border:none;"
            f" padding:6px 10px;}}"
            f"QPushButton:hover{{color:{NAVY};}}")
        b.clicked.connect(on_click)
        return b

    def _label(self, text, weight=MEDIUM, size=12, color=INK):
        lab = QtWidgets.QLabel(text)
        lab.setFont(hn(size, weight, spacing=1.0 if weight == MEDIUM else 0.0))
        lab.setStyleSheet(f"color:{color};")
        return lab

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

        # url row
        top = QtWidgets.QHBoxLayout()
        top.setSpacing(14)
        self.url_edit = QtWidgets.QLineEdit()
        self.url_edit.setFont(hn(15, LIGHT))
        self.url_edit.setPlaceholderText("paste a youtube link")
        self.url_edit.setStyleSheet(
            f"QLineEdit{{background:transparent; color:{INK}; border:none;"
            f" border-bottom:1px solid {INK}; padding:6px 0;}}")
        self.url_edit.returnPressed.connect(self._load)
        top.addWidget(self.url_edit, 1)
        top.addWidget(self._flat_button("LOAD", self._load))
        root.addLayout(top)

        # video framed in ink
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

        # controls row
        ctl = QtWidgets.QHBoxLayout()
        ctl.setSpacing(14)
        self.play_btn = self._flat_button("PLAY", self.engine.play_pause)
        self.play_btn.setFixedWidth(74)
        ctl.addWidget(self.play_btn)
        self.time_lbl = self._label("0:00 / 0:00", MEDIUM, 13)
        ctl.addWidget(self.time_lbl)
        ctl.addSpacing(10)

        ctl.addWidget(self._label("SPEED", MEDIUM, 11, MUTED))
        self.speed = self._slider(25, 200, 100, 130, NAVY)
        self.speed.valueChanged.connect(self._on_speed)
        ctl.addWidget(self.speed)
        self.speed_lbl = self._label("1.00x", LIGHT, 12)
        self.speed_lbl.setFixedWidth(46)
        ctl.addWidget(self.speed_lbl)
        ctl.addSpacing(10)

        ctl.addWidget(self._label("VOL", MEDIUM, 11, MUTED))
        self.volume = self._slider(0, 100, 100, 110, GREEN)
        self.volume.valueChanged.connect(self._on_volume)
        ctl.addWidget(self.volume)
        self.volume_lbl = self._label("100%", LIGHT, 12)
        self.volume_lbl.setFixedWidth(40)
        ctl.addWidget(self.volume_lbl)
        ctl.addStretch(1)
        root.addLayout(ctl)

        self.status = QtWidgets.QLineEdit("no song loaded")
        self.status.setReadOnly(True)
        self.status.setFont(hn(12, LIGHT))
        self.status.setStyleSheet(
            f"background:transparent; color:{MUTED}; border:none;")
        root.addWidget(self.status)

    # ---- engine signal handlers ----
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
            f"Songbird Archive Streamer — design_b — {title}" if title
            else "Songbird Archive Streamer — design_b")
        self._zoom = 1.0
        self._nx = self._ny = 0.5
        self._apply_video_geometry(None)
        self.url_edit.clearFocus()

    def _on_playing(self, playing):
        self.play_btn.setText("PAUSE" if playing else "PLAY")

    # ---- controls ----
    def _load(self):
        self.engine.load(self.url_edit.text())

    def _on_speed(self, value):
        rate = value / 100.0
        self.engine.set_speed(rate)
        self.speed_lbl.setText(f"{rate:.2f}x")

    def _on_volume(self, value):
        self.engine.set_volume(int(value))
        self.volume_lbl.setText(f"{int(value)}%")

    def _toggle_mute(self):
        if self.volume.value() > 0:
            self._pre_mute_volume = self.volume.value()
            self.volume.setValue(0)
        else:
            self.volume.setValue(self._pre_mute_volume or 100)

    # ---- zoom (unchanged math) ----
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

    # ---- keyboard ----
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
        self.engine.close()
        super().closeEvent(e)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = Window()
    win.show()
    win.engine.attach_video(int(win.videoframe.winId()))
    sys.exit(app.exec())

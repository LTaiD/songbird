#!/usr/bin/env python3

import html
import os
import shutil
import subprocess
import sys
import threading

import numpy as np
import vlc
import yt_dlp
from PySide6 import QtCore, QtGui, QtWidgets

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from songbird.links import links as resolve_links
from songbird.matcher import match as match_audio

WAVE_BINS = 1600


try:
    from yt_dlp.globals import supported_remote_components
    for _c in ("ejs:github", "ejs:npm"):
        if _c not in supported_remote_components.value:
            supported_remote_components.value.append(_c)
except Exception:
    pass

POLL_MS = 150
TIMELINE_HEIGHT = 38
SEEK_STEP_MS = 5000
SEEK_REPEAT_MS = 150


def fmt_time(ms):
    if ms is None or ms < 0:
        ms = 0
    s = int(ms // 1000)
    return f"{s // 60}:{s % 60:02d}"


class Timeline(QtWidgets.QWidget):

    seekRequested = QtCore.Signal(float)

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

    def _frac(self, x):
        return min(1.0, max(0.0, x / max(1, self.width())))

    def set_position(self, frac):
        self.position = min(1.0, max(0.0, frac))
        self.update()

    def set_peaks(self, peaks):
        self.peaks = peaks
        self.update()

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
            return

        handle = self._handle_at(x)
        if handle is not None:
            self._drag_handle = handle
            return

        self.seeking = True
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
            self.seeking = False
            self._drag_handle = None

    def mouseDoubleClickEvent(self, e):

        self.clear_section()

    def clear_section(self):
        self.sec_a = self.sec_b = self._pending_first = None
        self.update()

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        w, h = self.width(), self.height()
        mid = h // 2
        p.fillRect(self.rect(), QtGui.QColor("#1e1e1e"))
        pos_x = self.position * w

        has_sec = self.sec_a is not None and self.sec_b is not None
        xa = self.sec_a * w if has_sec else 0.0
        xb = self.sec_b * w if has_sec else 0.0

        if self.peaks is not None and len(self.peaks) and w > 0:
            n = len(self.peaks)
            half = h / 2 - 2
            grey = QtGui.QColor("#5a5a5a")
            blue = QtGui.QColor("#5f86bd")
            blue_lit = QtGui.QColor("#8fb6ee")
            for x in range(w):
                amp = float(self.peaks[int(x / w * n)])
                bar = max(1.0, amp * half)
                played = x <= pos_x
                if has_sec:

                    if xa <= x <= xb:
                        color = blue_lit if played else blue
                    else:
                        color = grey
                else:

                    color = blue_lit if played else grey
                p.setPen(color)
                p.drawLine(x, int(mid - bar), x, int(mid + bar))
        else:

            p.setPen(QtGui.QPen(QtGui.QColor("#444"), 3))
            p.drawLine(0, mid, w, mid)

        if has_sec:
            p.fillRect(int(xa) - 1, 0, 3, h, QtGui.QColor("#cfe0f5"))
            p.fillRect(int(xb) - 1, 0, 3, h, QtGui.QColor("#cfe0f5"))
        elif self._pending_first is not None:

            p.fillRect(int(self._pending_first * w) - 1, 0, 3, h,
                       QtGui.QColor("#cfe0f5"))

        x = int(pos_x)
        p.setPen(QtGui.QPen(QtGui.QColor("#f0f0f0"), 2))
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


class SongbirdArchiveStreamer(QtWidgets.QWidget):
    _resolved = QtCore.Signal(str, str, str, float)
    _failed = QtCore.Signal(str)
    _waveformReady = QtCore.Signal(object, int)
    _waveformFailed = QtCore.Signal(str, int)
    _matchDone = QtCore.Signal(object)
    _matchFailed = QtCore.Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Songbird Archive Streamer")
        self.resize(960, 620)
        self.setStyleSheet("background:#121212; color:#ccc;")

        self.vlc = vlc.Instance("--no-videotoolbox")
        self.player = self.vlc.media_player_new()
        self.media = None
        self._pending_seek = None
        self._wave_gen = 0
        self._duration_ms = 0
        self._title = ""

        self._sec_armed = False
        self._sec_awaiting = False

        self._zoom = 1.0
        self._nx = 0.5
        self._ny = 0.5
        self.ZOOM_MIN = 1.0
        self.ZOOM_MAX = 8.0

        self._audio_url = ""
        self._matching = False

        self._build_ui()
        self._resolved.connect(self._set_media)
        self._failed.connect(self._set_status)
        self._waveformReady.connect(self._on_waveform)
        self._waveformFailed.connect(self._on_waveform_failed)
        self._matchDone.connect(self._on_match_done)
        self._matchFailed.connect(self._on_match_failed)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._poll)
        self.timer.start(POLL_MS)

        self._seek_dir = 0
        self._seek_timer = QtCore.QTimer(self)
        self._seek_timer.setInterval(SEEK_REPEAT_MS)
        self._seek_timer.timeout.connect(
            lambda: self._seek_relative(self._seek_dir * SEEK_STEP_MS))
        QtWidgets.QApplication.instance().installEventFilter(self)

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        top = QtWidgets.QHBoxLayout()
        self.url_edit = QtWidgets.QLineEdit()
        self.url_edit.setPlaceholderText("paste YouTube or TikTok link")
        self.url_edit.returnPressed.connect(self.load)
        load_btn = QtWidgets.QPushButton("Load")
        load_btn.clicked.connect(self.load)
        self.match_file_btn = QtWidgets.QPushButton("File Upload")
        self.match_file_btn.clicked.connect(self.match_file)
        self.match_loaded_btn = QtWidgets.QPushButton("Identify Song")
        self.match_loaded_btn.setEnabled(False)
        self.match_loaded_btn.clicked.connect(self.match_loaded)
        top.addWidget(self.url_edit)
        top.addWidget(load_btn)
        top.addWidget(self.match_file_btn)
        top.addWidget(self.match_loaded_btn)
        root.addLayout(top)

        self.video_container = VideoContainer()
        self.video_container.setStyleSheet("background:black;")
        self.video_container.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                           QtWidgets.QSizePolicy.Expanding)
        self.video_container.resized.connect(self._on_container_resized)
        root.addWidget(self.video_container, 1)

        self.videoframe = VideoFrame(self.video_container)
        self.videoframe.setStyleSheet("background:black;")
        self.videoframe.setAttribute(QtCore.Qt.WA_NativeWindow, True)
        self.videoframe.clicked.connect(self.toggle_play)
        self.videoframe.wheelZoom.connect(self._on_wheel_zoom)
        self.videoframe.pinchZoom.connect(self._on_pinch_zoom)

        self.timeline = Timeline()
        self.timeline.seekRequested.connect(self._seek_fraction)
        root.addWidget(self.timeline)

        ctl = QtWidgets.QHBoxLayout()
        self.play_btn = QtWidgets.QPushButton("Play")
        self.play_btn.setFixedWidth(70)
        self.play_btn.clicked.connect(self.toggle_play)
        ctl.addWidget(self.play_btn)

        self.time_lbl = QtWidgets.QLabel("0:00 / 0:00")
        ctl.addWidget(self.time_lbl)
        ctl.addSpacing(12)

        ctl.addWidget(QtWidgets.QLabel("Speed"))
        self.speed = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.speed.setMinimum(25)
        self.speed.setMaximum(200)
        self.speed.setValue(100)
        self.speed.setFixedWidth(150)
        self.speed.valueChanged.connect(self._on_speed)
        ctl.addWidget(self.speed)
        self.speed_lbl = QtWidgets.QLabel("1.00x")
        self.speed_lbl.setFixedWidth(48)
        ctl.addWidget(self.speed_lbl)
        ctl.addStretch(1)
        root.addLayout(ctl)

        self.status = QtWidgets.QLineEdit("paste YouTube or TikTok link")
        self.status.setReadOnly(True)
        self.status.setStyleSheet(
            "background:#121212; color:#999; border:none;")
        root.addWidget(self.status)

        self.result = QtWidgets.QLabel("")
        self.result.setTextFormat(QtCore.Qt.RichText)
        self.result.setOpenExternalLinks(True)
        self.result.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        self.result.setWordWrap(True)
        self.result.setStyleSheet(
            "background:#1b1b1b; color:#eee; padding:10px; border-radius:6px;")
        self.result.setVisible(False)
        root.addWidget(self.result)

    def _embed(self):

        handle = int(self.videoframe.winId())
        if sys.platform.startswith("win"):
            self.player.set_hwnd(handle)
        elif sys.platform == "darwin":
            self.player.set_nsobject(handle)
        else:
            self.player.set_xwindow(handle)

        self.player.video_set_mouse_input(False)
        self.player.video_set_key_input(False)

    def _on_container_resized(self):
        self._apply_video_geometry(None)

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

    def load(self):
        url = self.url_edit.text().strip()
        if not url:
            return
        self._set_status("resolving…")
        threading.Thread(target=self._resolve, args=(url,), daemon=True).start()

    def _resolve(self, url):

        opts = {"format": "best[ext=mp4]/best", "quiet": True,
                "noplaylist": True, "remote_components": ["ejs:github"]}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)

            auds = [f for f in info.get("formats", [])
                    if f.get("acodec") not in (None, "none")
                    and f.get("vcodec") in (None, "none") and f.get("url")]
            auds.sort(key=lambda f: (str(f.get("protocol", "")).startswith("m3u8"),
                                     f.get("abr") or 1e9))
            audio_url = auds[0]["url"] if auds else ""
            self._resolved.emit(info["url"], info.get("title", ""), audio_url,
                                float(info.get("duration") or 0))
        except Exception as exc:
            self._failed.emit(f"error: {exc}")

    @QtCore.Slot(str, str, str, float)
    def _set_media(self, stream, title, audio_url="", duration=0.0):
        self.media = self.vlc.media_new(stream)
        self._pending_seek = None
        self._audio_url = audio_url or stream
        self.match_loaded_btn.setEnabled(True)
        self._title = title
        self._duration_ms = int(duration * 1000)
        self._sec_armed = self._sec_awaiting = False
        self.timeline.clear_section()
        self._zoom = 1.0
        self._nx = self._ny = 0.5
        self._apply_video_geometry(None)
        self.player.set_media(self.media)
        self._embed()
        self.player.play()
        self.player.set_rate(self.speed.value() / 100.0)
        self.url_edit.clearFocus()
        self.play_btn.setText("Pause")
        self._set_status(title)
        self.setWindowTitle(
            f"Songbird Archive Streamer — {title}" if title
            else "Songbird Archive Streamer")

        self._wave_gen += 1
        self.timeline.set_peaks(None)
        if title:
            self._set_status(f"{title}  ·  computing waveform…")
        src = audio_url or stream
        threading.Thread(target=self._compute_waveform,
                         args=(src, self._wave_gen), daemon=True).start()

    def _compute_waveform(self, src, gen):

        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            self._waveformFailed.emit("waveform unavailable: ffmpeg not installed", gen)
            return
        cmd = [ffmpeg, "-nostdin", "-loglevel", "error", "-i", src,
               "-ac", "1", "-ar", "4000", "-f", "s16le", "-"]
        try:

            proc = subprocess.run(cmd, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, timeout=90, check=False)
            out = proc.stdout
        except subprocess.TimeoutExpired:
            self._waveformFailed.emit("waveform unavailable: audio decode timed out", gen)
            return
        except Exception as exc:
            self._waveformFailed.emit(f"waveform unavailable: {exc}", gen)
            return
        if not out:
            reason = (proc.stderr or b"").decode("utf-8", "replace").strip()
            reason = reason.splitlines()[-1] if reason else "no audio decoded"
            self._waveformFailed.emit(f"waveform unavailable: {reason}", gen)
            return
        samples = np.frombuffer(out, dtype=np.int16).astype(np.float32)
        if samples.size < WAVE_BINS:
            self._waveformFailed.emit("waveform unavailable: audio too short", gen)
            return
        binsize = samples.size // WAVE_BINS
        usable = samples[:binsize * WAVE_BINS].reshape(WAVE_BINS, binsize)
        peaks = np.abs(usable).max(axis=1)
        peak = peaks.max()
        if peak > 0:
            peaks = peaks / peak
        self._waveformReady.emit(peaks, gen)

    @QtCore.Slot(object, int)
    def _on_waveform(self, peaks, gen):
        if gen == self._wave_gen:
            self.timeline.set_peaks(peaks)
            self._set_status(self._title)

    @QtCore.Slot(str, int)
    def _on_waveform_failed(self, reason, gen):
        if gen == self._wave_gen:
            self._set_status(reason)

    def _ended(self):

        return self.player.get_state() in (
            vlc.State.Ended, vlc.State.Stopped, vlc.State.Error)

    def _restart(self, fraction=0.0):

        if self.media is None:
            return
        self.player.set_media(self.media)
        self.player.play()
        self.player.set_rate(self.speed.value() / 100.0)
        self._pending_seek = fraction
        self.play_btn.setText("Pause")

    def toggle_play(self):
        if self._ended():
            self._restart(0.0)
        elif self.player.is_playing():
            self.player.pause()
            self.play_btn.setText("Play")
        else:
            self.player.play()
            self.play_btn.setText("Pause")

    def _on_speed(self, value):
        rate = value / 100.0
        self.player.set_rate(rate)
        self.speed_lbl.setText(f"{rate:.2f}x")

    def _seek_fraction(self, frac):
        if self._ended():
            self._restart(frac)
        else:
            self.player.set_position(frac)

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
                    self._seek_relative(self._seek_dir * SEEK_STEP_MS)
                    self._seek_timer.start()
                else:
                    self._seek_timer.stop()
                return True
        return super().eventFilter(obj, event)

    def _seek_relative(self, delta_ms):
        length = self.player.get_length()
        if length <= 0:
            length = self._duration_ms
        if length <= 0:
            return
        pos = max(0, self.player.get_time())
        new = max(0, min(length - 1, pos + delta_ms))
        frac = new / length
        if self._ended():
            self._restart(frac)
        else:
            self.player.set_time(int(new))
        self.timeline.set_position(frac)

    @QtCore.Slot(str)
    def _set_status(self, msg):
        self.status.setText(str(msg))
        self.status.setCursorPosition(0)

    def _poll(self):
        state = self.player.get_state()

        if state == vlc.State.Playing and self.url_edit.hasFocus():
            self.url_edit.clearFocus()

        length = self.player.get_length()
        if length <= 0:
            length = self._duration_ms

        if self._pending_seek is not None and state == vlc.State.Playing and length > 0:
            self.player.set_position(self._pending_seek)
            self._pending_seek = None

        if length > 0:
            pos = self.player.get_time()
            if not self.timeline.seeking and self._pending_seek is None:
                self.timeline.set_position(pos / length)
            self.time_lbl.setText(f"{fmt_time(pos)} / {fmt_time(length)}")

            a, b = self.timeline.sec_a, self.timeline.sec_b
            has_sec = a is not None and b is not None and b > a
            if has_sec and self.player.is_playing() and not self.timeline.seeking:
                pos_f = pos / length
                if a <= pos_f < b:
                    self._sec_armed = True
                    self._sec_awaiting = False
                elif not self._sec_awaiting:

                    self.player.set_time(int(a * length))
                    self._sec_awaiting = True
                    self._sec_armed = False

            elif (not has_sec or self.timeline.seeking
                    or state in (vlc.State.Paused, vlc.State.Stopped,
                                 vlc.State.Ended)):

                self._sec_awaiting = False

        if state == vlc.State.Ended:
            self.play_btn.setText("Play")
            self.timeline.set_position(1.0)

    def match_file(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Choose a recording", "",
            "Audio/Video (*.mp3 *.wav *.m4a *.flac *.ogg *.mp4 *.mov *.mkv *.webm)")
        if path:
            self._start_match(path)

    def match_loaded(self):
        if self._audio_url:
            self._start_match(self._audio_url)

    def _start_match(self, src):
        if self._matching:
            return
        self._matching = True
        self.match_file_btn.setEnabled(False)
        self.match_loaded_btn.setEnabled(False)
        self.result.setVisible(False)
        self._set_status("identifying song… (CPU, this can take a minute)")
        threading.Thread(target=self._run_match, args=(src,), daemon=True).start()

    def _run_match(self, src):
        try:
            self._matchDone.emit(match_audio(src))
        except Exception as exc:
            self._matchFailed.emit(f"match error: {exc}")

    @QtCore.Slot(object)
    def _on_match_done(self, pred):
        self._matching = False
        self.match_file_btn.setEnabled(True)
        self.match_loaded_btn.setEnabled(bool(self._audio_url))
        if not pred:
            self._set_status("no match: reference index is empty or unreadable")
            return
        song, artist, apple_url = pred
        apple, spotify, tiktok = resolve_links(song, artist, apple_url)
        self.result.setText(
            f"<b>{html.escape(song)}</b><br>{html.escape(artist)}<br>"
            f'<a style="color:#4da3ff" href="{html.escape(apple)}">Apple Music</a>'
            f' &nbsp; <a style="color:#4da3ff" href="{html.escape(spotify)}">Spotify</a>'
            f' &nbsp; <a style="color:#4da3ff" href="{html.escape(tiktok)}">TikTok</a>')
        self.result.setVisible(True)
        self._set_status("done")

    @QtCore.Slot(str)
    def _on_match_failed(self, msg):
        self._matching = False
        self.match_file_btn.setEnabled(True)
        self.match_loaded_btn.setEnabled(bool(self._audio_url))
        self._set_status(msg)

    def closeEvent(self, e):
        try:
            self.player.stop()
        except Exception:
            pass
        super().closeEvent(e)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = SongbirdArchiveStreamer()
    win.show()
    sys.exit(app.exec())

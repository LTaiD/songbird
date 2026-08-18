#!/usr/bin/env python3

import shutil
import subprocess
import sys
import threading

import numpy as np
import vlc
import yt_dlp
from PySide6 import QtCore


try:
    from yt_dlp.globals import supported_remote_components
    for _c in ("ejs:github", "ejs:npm"):
        if _c not in supported_remote_components.value:
            supported_remote_components.value.append(_c)
except Exception:
    pass

WAVE_BINS = 1600
POLL_MS = 150
RENDER_MS = 33
CATCHUP_MS = 250
SEEK_STEP_MS = 5000
SEEK_REPEAT_MS = 150
SEEK_LIVE_MARGIN_MS = 250
SEEK_SETTLE_MAX = 80


def fmt_time(ms):
    if ms is None or ms < 0:
        ms = 0
    s = int(ms // 1000)
    return f"{s // 60}:{s % 60:02d}"


class Engine(QtCore.QObject):

    loaded = QtCore.Signal(str)
    status = QtCore.Signal(str)
    waveform = QtCore.Signal(object)
    section_changed = QtCore.Signal(object, object)
    tick = QtCore.Signal(float, int, int)
    playing_changed = QtCore.Signal(bool)

    _resolved = QtCore.Signal(str, str, str, float, str)
    _waveformReady = QtCore.Signal(object, int)
    _waveformFailed = QtCore.Signal(str, int)

    def __init__(self):
        super().__init__()

        self.vlc = vlc.Instance("--no-videotoolbox", "--quiet")
        self.player = self.vlc.media_player_new()
        self.media = None
        self._winid = None
        self._audio_src = ""
        self._page_url = ""
        self._pending_seek = None
        self._wave_gen = 0
        self._duration_ms = 0
        self._title = ""
        self._seek_target_ms = None
        self._seek_settle_polls = 0
        self._sec_a = None
        self._sec_b = None
        self._sec_armed = False
        self._sec_awaiting = False
        self._scrubbing = False
        self._speed = 1.0
        self._volume = 100
        self._loop = False
        self._load_retry = 0

        self._disp_ms = 0.0
        self._length_ms = 0
        self._anchor_ms = 0.0
        self._interp_active = False
        self._anchor_clock = QtCore.QElapsedTimer()
        self._anchor_clock.start()

        self._resolved.connect(self._set_media)
        self._waveformReady.connect(self._on_waveform)
        self._waveformFailed.connect(self._on_waveform_failed)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._poll)
        self.timer.start(POLL_MS)

        self.render_timer = QtCore.QTimer(self)
        self.render_timer.timeout.connect(self._render)
        self.render_timer.start(RENDER_MS)

    def attach_video(self, winid):
        self._winid = int(winid)
        self._embed()

    def _embed(self):
        if self._winid is None:
            return
        h = self._winid
        if sys.platform.startswith("win"):
            self.player.set_hwnd(h)
        elif sys.platform == "darwin":
            self.player.set_nsobject(h)
        else:
            self.player.set_xwindow(h)

        self.player.video_set_mouse_input(False)
        self.player.video_set_key_input(False)

    def is_playing(self):
        return self.player.is_playing()

    def match_source(self):
        return self._page_url

    def set_speed(self, rate):

        self._set_anchor(self._disp_ms, self._interp_active)
        self._speed = float(rate)
        self.player.set_rate(self._speed)

    def set_volume(self, vol):
        self._volume = int(vol)
        self.player.audio_set_volume(self._volume)

    def set_loop(self, on):
        self._loop = bool(on)

    def set_scrubbing(self, scrubbing):

        self._scrubbing = bool(scrubbing)

    def set_section(self, a, b):

        self._sec_a, self._sec_b = a, b
        self._sec_armed = self._sec_awaiting = False

    def clear_section(self):

        self._sec_a = self._sec_b = None
        self._sec_armed = self._sec_awaiting = False
        self.section_changed.emit(None, None)

    def play_pause(self):
        if self._ended():
            self._restart(0.0)
        elif self.player.is_playing():
            self.player.pause()
            self._set_anchor(self._disp_ms, False)
            self.playing_changed.emit(False)
        else:
            self.player.play()
            self._set_anchor(self._disp_ms, True)
            self.playing_changed.emit(True)

    def _ended(self):
        return self.player.get_state() in (
            vlc.State.Ended, vlc.State.Stopped, vlc.State.Error)

    def _restart(self, fraction=0.0):
        if self.media is None:
            return
        self.player.set_media(self.media)
        self.player.play()
        self.player.set_rate(self._speed)
        self._pending_seek = fraction
        self.playing_changed.emit(True)

    def load(self, url):
        url = (url or "").strip()
        if not url:
            return
        self._page_url = url
        self._load_retry = 0
        self.status.emit("resolving…")
        threading.Thread(target=self._resolve, args=(url,), daemon=True).start()

    def _retry_load(self):

        self._load_retry += 1
        self.status.emit("stream expired — re-resolving…")
        threading.Thread(target=self._resolve, args=(self._page_url,), daemon=True).start()

    def _resolve(self, url):

        opts = {"format": "best[ext=mp4]/best", "quiet": True, "cachedir": False,
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
                                float(info.get("duration") or 0),
                                str(info.get("id") or ""))
        except Exception as exc:
            self.status.emit(f"error: {exc}")

    @QtCore.Slot(str, str, str, float, str)
    def _set_media(self, stream, title, audio_url="", duration=0.0, video_id=""):
        self.media = self.vlc.media_new(stream)
        self._pending_seek = None
        self._audio_src = audio_url or stream
        self._title = title
        self._duration_ms = int(duration * 1000)
        self._sec_armed = self._sec_awaiting = False
        self._seek_target_ms = None
        self._disp_ms = 0.0
        self._length_ms = 0
        self._set_anchor(0, False)
        self.clear_section()
        self.player.set_media(self.media)
        self._embed()
        self.player.play()
        self.player.set_rate(self._speed)
        self.player.audio_set_volume(self._volume)
        self.playing_changed.emit(True)
        self.loaded.emit(title)
        self.status.emit(title)

        self._wave_gen += 1
        self.waveform.emit(None)
        if title:
            self.status.emit(f"{title}  ·  computing waveform…")
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
            self.waveform.emit(peaks)
            self.status.emit(self._title)

    @QtCore.Slot(str, int)
    def _on_waveform_failed(self, reason, gen):
        if gen != self._wave_gen:
            return
        low = reason.lower()
        if ("403" in low or "forbidden" in low) and self._load_retry < 1 and self._page_url:
            self._retry_load()
            return
        self.status.emit(reason)

    def _length(self):
        length = self.player.get_length()
        return length if length > 0 else self._duration_ms

    def _begin_seek(self, target_ms, length):

        if length <= 0:
            return
        target = max(0, min(length - 1, int(target_ms)))
        self._seek_target_ms = target
        self._seek_settle_polls = 0
        self._length_ms = length
        self._disp_ms = target
        self._set_anchor(target, False)
        self.tick.emit(target / length, target, int(length))

    def seek_fraction(self, frac):
        if self._ended():
            self._restart(frac)
        else:
            self.player.set_position(frac)
        self._begin_seek(frac * self._length(), self._length())

    def seek_relative(self, delta_ms):
        length = self._length()
        if length <= 0:
            return
        pos = max(0, self.player.get_time())
        new = max(0, min(length - 1, pos + delta_ms))
        if self._ended():
            self._restart(new / length)
        else:
            self.player.set_time(int(new))
        self._begin_seek(new, length)

    def _set_anchor(self, ms, advancing):
        self._anchor_ms = float(ms)
        self._anchor_clock.restart()
        self._interp_active = bool(advancing)

    def _render(self):
        length = self._length_ms
        if length <= 0:
            return
        if self._interp_active:
            ms = self._anchor_ms + self._anchor_clock.elapsed() * self._speed
        else:
            ms = self._anchor_ms
        ms = max(0.0, min(float(length), ms))
        self._disp_ms = ms
        self.tick.emit(ms / length, int(ms), int(length))

    def _poll(self):
        state = self.player.get_state()
        length = self._length()

        if (state == vlc.State.Error and self.media is not None
                and self._page_url and self._load_retry < 1):
            self._retry_load()
            return

        if self._pending_seek is not None and state == vlc.State.Playing and length > 0:
            self.player.set_position(self._pending_seek)
            self._begin_seek(self._pending_seek * length, length)
            self._pending_seek = None

        if length > 0:
            self._length_ms = length
            pos = max(0, self.player.get_time())
            disp = pos
            if self._seek_target_ms is not None:
                self._seek_settle_polls += 1
                if (pos > self._seek_target_ms + SEEK_LIVE_MARGIN_MS
                        or self._seek_settle_polls > SEEK_SETTLE_MAX):
                    self._seek_target_ms = None
                else:
                    disp = self._seek_target_ms

            held = self._seek_target_ms is not None
            if held:
                self._set_anchor(self._seek_target_ms, False)
            elif self._scrubbing:
                self._set_anchor(disp, False)
            elif state == vlc.State.Buffering:
                self._set_anchor(self._disp_ms, False)
            elif state == vlc.State.Playing:
                drift = disp - self._disp_ms
                base = disp if drift > CATCHUP_MS else self._disp_ms
                self._set_anchor(base, True)
            else:
                self._set_anchor(disp, False)

            a, b = self._sec_a, self._sec_b
            has_sec = a is not None and b is not None and b > a
            if has_sec and self.player.is_playing() and not self._scrubbing:
                pos_f = pos / length
                if a <= pos_f < b:
                    self._sec_armed = True
                    self._sec_awaiting = False
                elif not self._sec_awaiting:
                    self.player.set_time(int(a * length))
                    self._begin_seek(a * length, length)
                    self._sec_awaiting = True
                    self._sec_armed = False

            elif (not has_sec or self._scrubbing
                    or state in (vlc.State.Paused, vlc.State.Stopped,
                                 vlc.State.Ended)):
                self._sec_awaiting = False

        if state == vlc.State.Ended:
            if self._loop:
                self._restart(0.0)
            else:
                self.playing_changed.emit(False)
                if length > 0:
                    self._length_ms = length
                    self._set_anchor(length, False)
                    self.tick.emit(1.0, length, length)

    def close(self):
        try:
            self.player.stop()
        except Exception:
            pass

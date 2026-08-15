#!/usr/bin/env python3
"""
Songbird Archive Streamer shared backend — the "engine".

All the non-visual plumbing lives here so UI prototypes can stay thin: yt-dlp
resolving, libVLC playback, the audio-waveform decode, position polling, the
keyframe-seek settling, the A-B section loop, and speed/volume. A UI drives it
through plain methods and reacts to its signals; it owns no widgets except the
native video surface (attached via a window id).

This mirrors the logic in link-stream.py (the frozen reference app) — if you
change playback behavior, change it here and the reference both, or promote a
chosen design back into a single file later.
"""

import shutil
import subprocess
import sys
import threading

import numpy as np
import vlc
import yt_dlp
from PySide6 import QtCore

# When yt-dlp runs as a library the remote-component allow-list isn't pre-filled,
# so register YouTube's JS challenge solver components up front.
try:
    from yt_dlp.globals import supported_remote_components
    for _c in ("ejs:github", "ejs:npm"):
        if _c not in supported_remote_components.value:
            supported_remote_components.value.append(_c)
except Exception:
    pass

WAVE_BINS = 1600           # amplitude buckets computed for the waveform
POLL_MS = 150              # playback poll interval (VLC state / seek / loop)
RENDER_MS = 33             # playhead render interval (~30fps smooth interpolation)
CATCHUP_MS = 250           # only ease the playhead FORWARD if it falls this far behind
SEEK_STEP_MS = 5000        # arrow-key seek step
SEEK_REPEAT_MS = 150       # how often a held arrow key seeks again
SEEK_LIVE_MARGIN_MS = 250  # resume live playhead once get_time passes the seek target
SEEK_SETTLE_MAX = 80       # polls (~12s) to hold the playhead at the target


def fmt_time(ms):
    """milliseconds formatted as m:ss."""
    if ms is None or ms < 0:
        ms = 0
    s = int(ms // 1000)
    return f"{s // 60}:{s % 60:02d}"


class Engine(QtCore.QObject):
    """Headless player engine. Drive it with the public methods; react to signals."""

    # --- public signals (UI listens to these) -------------------------
    loaded = QtCore.Signal(str)                  # title, after media starts
    status = QtCore.Signal(str)                  # status / error / progress text
    waveform = QtCore.Signal(object)             # numpy peaks (or None to clear)
    section_changed = QtCore.Signal(object, object)  # a, b (floats or None)
    tick = QtCore.Signal(float, int, int)        # disp_frac, disp_ms, length_ms
    playing_changed = QtCore.Signal(bool)        # play/pause state for the UI

    # --- internal worker-thread -> main-thread marshalling ------------
    _resolved = QtCore.Signal(str, str, str, float, str)
    _waveformReady = QtCore.Signal(object, int)
    _waveformFailed = QtCore.Signal(str, int)

    def __init__(self):
        super().__init__()
        self.vlc = vlc.Instance()
        self.player = self.vlc.media_player_new()
        self.media = None
        self._winid = None
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

        # Smooth-playhead interpolation: the 150ms VLC poll anchors a local clock
        # and a faster render timer glides the playhead between polls, so it
        # doesn't step/teleport with VLC's coarse get_time().
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

    # --- video surface -------------------------------------------------
    def attach_video(self, winid):
        """Give the engine the native window id of the UI's video widget."""
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
        # Let the UI (Qt) receive clicks/keys instead of libVLC eating them.
        self.player.video_set_mouse_input(False)
        self.player.video_set_key_input(False)

    # --- settings ------------------------------------------------------
    def is_playing(self):
        return self.player.is_playing()

    def set_speed(self, rate):
        # Re-anchor first so the new rate only applies to time from here on.
        self._set_anchor(self._disp_ms, self._interp_active)
        self._speed = float(rate)
        self.player.set_rate(self._speed)

    def set_volume(self, vol):
        self._volume = int(vol)
        self.player.audio_set_volume(self._volume)

    def set_scrubbing(self, scrubbing):
        # The UI tells us when the user is dragging the playhead, so we don't
        # fight it (skip the live playhead update and section enforcement).
        self._scrubbing = bool(scrubbing)

    # --- sections ------------------------------------------------------
    def set_section(self, a, b):
        # UI-initiated; store without echoing back (no section_changed emit).
        self._sec_a, self._sec_b = a, b
        self._sec_armed = self._sec_awaiting = False

    def clear_section(self):
        # Engine-initiated (e.g. new video); notify the UI to clear its drawing.
        self._sec_a = self._sec_b = None
        self._sec_armed = self._sec_awaiting = False
        self.section_changed.emit(None, None)

    # --- transport -----------------------------------------------------
    def play_pause(self):
        if self._ended():
            self._restart(0.0)
        elif self.player.is_playing():
            self.player.pause()
            self._set_anchor(self._disp_ms, False)   # freeze playhead now
            self.playing_changed.emit(False)
        else:
            self.player.play()
            self._set_anchor(self._disp_ms, True)     # glide from here now
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

    # --- loading -------------------------------------------------------
    def load(self, url):
        url = (url or "").strip()
        if not url:
            return
        self.status.emit("resolving…")
        threading.Thread(target=self._resolve, args=(url,), daemon=True).start()

    def _resolve(self, url):
        opts = {"format": "best[ext=mp4]/best", "quiet": True,
                "noplaylist": True, "remote_components": ["ejs:github"]}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            # Smallest audio-only stream = fastest waveform decode.
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
        self._title = title
        self._duration_ms = int(duration * 1000)
        self._sec_armed = self._sec_awaiting = False
        self._seek_target_ms = None
        self._disp_ms = 0.0
        self._length_ms = 0
        self._set_anchor(0, False)           # playhead starts at zero
        self.clear_section()                 # new video -> clean slate
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
        if gen == self._wave_gen:
            self.status.emit(reason)

    # --- seeking -------------------------------------------------------
    def _length(self):
        length = self.player.get_length()
        return length if length > 0 else self._duration_ms

    def _begin_seek(self, target_ms, length):
        # Paint the playhead at the target now and suppress the backward
        # get_time() dip until playback rolls past it (handled in _poll).
        if length <= 0:
            return
        target = max(0, min(length - 1, int(target_ms)))
        self._seek_target_ms = target
        self._seek_settle_polls = 0
        self._length_ms = length
        self._disp_ms = target
        self._set_anchor(target, False)              # hold at target until settle
        self.tick.emit(target / length, target, int(length))   # instant feedback

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

    # --- smooth playhead -----------------------------------------------
    def _set_anchor(self, ms, advancing):
        """Anchor the local playback clock; `advancing` glides, else freezes."""
        self._anchor_ms = float(ms)
        self._anchor_clock.restart()
        self._interp_active = bool(advancing)

    def _render(self):
        """~30fps: interpolate the playhead from the anchor and emit a tick."""
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

    # --- main loop -----------------------------------------------------
    def _poll(self):
        state = self.player.get_state()
        length = self._length()

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
            # Re-anchor the smooth clock to VLC. The playhead must never step
            # backward during playback (real backward jumps — seeks, loop wraps —
            # come through _begin_seek/the seek-hold below), so while playing we
            # only glide forward, easing forward if we've fallen behind.
            held = self._seek_target_ms is not None
            if held:
                self._set_anchor(self._seek_target_ms, False)   # hold at seek target
            elif self._scrubbing:
                self._set_anchor(disp, False)                   # follow the drag
            elif state == vlc.State.Buffering:
                self._set_anchor(self._disp_ms, False)          # stale time; don't move
            elif state == vlc.State.Playing:
                drift = disp - self._disp_ms
                base = disp if drift > CATCHUP_MS else self._disp_ms
                self._set_anchor(base, True)
            else:
                self._set_anchor(disp, False)                   # paused / stopped: hold

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
                # else: awaiting -> let playback roll into the section
            elif (not has_sec or self._scrubbing
                    or state in (vlc.State.Paused, vlc.State.Stopped,
                                 vlc.State.Ended)):
                self._sec_awaiting = False

        if state == vlc.State.Ended:
            self.playing_changed.emit(False)
            if length > 0:
                self._length_ms = length
                self._set_anchor(length, False)       # pin at the end
                self.tick.emit(1.0, length, length)

    def close(self):
        try:
            self.player.stop()
        except Exception:
            pass

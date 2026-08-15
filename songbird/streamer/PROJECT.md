# Songbird Archive Streamer — project reference

A barebones desktop app that plays a YouTube link in a window and lets you loop a
highlighted section of it. This doc is the context anchor — read it to resume
feature work later.

## How it works (architecture)
```
YouTube URL ──yt-dlp──▶ stream URL + audio URL + duration
                         │
            libVLC (python-vlc) ──▶ video into a Qt native window
                         │
            ffmpeg + numpy ──▶ audio waveform (amplitude peaks)
                         │
            PySide6 (Qt) UI ──▶ window, timeline, controls, keyboard
```
- **Qt, not Tkinter:** Tkinter bus-errors when libVLC draws into its NSView on macOS;
  Qt embeds libVLC reliably via the widget's `winId()`.
- Two ways to read the code:
  - `link-stream.py` — the **frozen reference**: the complete app in one file.
  - `engine.py` + `prototypes/design_*.py` — the **design sandbox**: backend split out
    (`engine.py`) so UI prototypes stay thin. See `prototypes/README.md`.

## Features
- Load a YouTube URL (Load button or Enter); status line shows progress/errors (copyable).
- Play / pause / resume — button, click the video, or **Space**.
- Playback speed 0.25×–2.0× (slider).
- Volume 0–100% (slider) + **M** mute (remembers level); **↑/↓** adjust volume.
- Seek: click or drag the bar (vertical playhead); **←/→** seek ±5s, hold to scrub.
- Audio **waveform** drawn in the seek bar; played portion brighter.
- **Loop sections:** Shift+click two points to set an A–B region (first edge previews on
  the first click); drag the light-blue edge handles to resize; double-click to clear.
  Playback loops within it and snaps in if you start before it. Cleared on a new video.
- **Zoom** the video: Ctrl+scroll or trackpad pinch, origin at the pointer, clipped to
  the player area (geometry-based; libVLC has no pan API).
- No captions (by design).

## Controls
| Input | Action |
| --- | --- |
| Space | Play / pause |
| ← / → | Seek −/+ 5s (hold = continuous) |
| ↑ / ↓ | Volume +/− 5% |
| M | Mute toggle |
| Click video | Play / pause |
| Drag / click bar | Seek |
| Shift+click ×2 | Define A–B loop section |
| Drag edge handle | Resize section |
| Double-click bar | Clear section |
| Ctrl+scroll / pinch | Zoom video (pointer origin) |

## Setup & dependencies
- Python 3.9+ with Tkinter-free Qt UI; **VLC desktop app** installed (libVLC).
- `ffmpeg` (waveform decode) and `deno` (yt-dlp JS challenge solver) via Homebrew.
- Python pkgs (in `.venv`, see `requirements.txt`): `yt-dlp`, `python-vlc`, `PySide6`,
  `numpy`, `certifi`.
- macOS SSL: python.org Python ships without CA certs → run
  `"/Applications/Python 3.13/Install Certificates.command"` once (fixes `_ssl.c:1028`).
- Run: `cd songbird-archive-streamer && .venv/bin/python link-stream.py` (or a prototype,
  see below).

## Key design decisions / gotchas (the non-obvious stuff)
- **HLS length:** yt-dlp often returns an HLS stream where `player.get_length()` is `0`.
  We fall back to yt-dlp's `duration` so the playhead + looping work (`engine._length()`).
- **Seek dip:** after a seek, `get_time()` reports the target then dips back to the prior
  keyframe (1.7–5.2s) before rolling forward. `_begin_seek` holds the playhead at the
  target until playback passes it, so the bar never jumps backward.
- **Section loop machine:** `_sec_armed` / `_sec_awaiting` prevent re-seek churn from the
  keyframe dip; the latch is preserved through transient *Buffering* (long HLS seeks).
- **Waveform speed:** decode the **lowest-bitrate** audio (smallest download) — a 20-min
  video is ~1–2s vs a timeout for the highest-bitrate stream.
- **URL field focus:** dropped on play so arrow keys seek; editable again while paused.

## Feature backlog (not yet built)
- **Precise loop control** — frame-step (`,` / `.`) and fine-nudge the A/B edges.
- **Fullscreen** toggle (F / double-click the video).
- **Loop on/off toggle** (keep the section but pause looping) + **persist settings**
  (volume/speed, maybe last section) across restarts.

## Files
- `link-stream.py` — frozen reference app (single file).
- `engine.py` — shared backend (`Engine` class). `prototypes/design_*.py` — thin UIs.
- `PROJECT.md` (this), `prototypes/README.md`, `requirements.txt`.
</content>
</invoke>

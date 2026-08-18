# UI prototypes

A sandbox for trying different UI designs **without touching the working app**.

## The layout
- `../link-stream.py` — **the main app**: the Blue-Note "color-block" UI (promoted from
  `design_b.py`) with song identification, built on `engine.py`.
- `../engine.py` — the shared backend (player, yt-dlp, waveform, seeking, looping).
  All the plumbing lives here so each design file stays thin (just the look + layout).
- `shell.py` — the old plain-dark UI, kept as a runnable fallback. Self-contained (no engine).
  Run: `.venv/bin/python prototypes/shell.py`.

## Run a design
```bash
cd songbird-archive-streamer
.venv/bin/python prototypes/shell.py   # the fallback shell UI
```
The main app is one level up: `.venv/bin/python ../link-stream.py`.

## Try a new design
1. Copy the main app:  `cp ../link-stream.py prototypes/design_x.py`
2. Edit `design_x.py` — it's all UI: window layout, the `Timeline` drawing (`paintEvent`),
   colors/sizes, the controls row, the video frame. Change whatever you like.
   (Fix the `sys.path` inserts if you move it into `prototypes/`.)
3. Run it:  `.venv/bin/python prototypes/design_x.py`
4. Compare designs by running them one at a time.

## What goes where
- **Looks / layout / interaction** → the design file (`design_*.py`).
- **Playback behavior** (how seeking/looping/waveform/zoom *work*) → `engine.py`.
  Avoid changing `engine.py` while designing — every prototype shares it, so a break
  affects them all. If a design needs new engine behavior, add a method/signal to the
  `Engine` class rather than reaching into the player directly.

## How a design talks to the engine
The window creates `Engine()` and connects:
- **engine → UI signals:** `tick(frac, ms, length)` (move playhead + time label),
  `waveform(peaks)`, `section_changed(a, b)`, `status(msg)`, `loaded(title)`,
  `playing_changed(bool)`.
- **UI → engine methods:** `load(url)`, `play_pause()`, `set_speed(x)`, `set_volume(v)`,
  `seek_fraction(f)`, `seek_relative(ms)`, `set_section(a, b)`, `set_scrubbing(bool)`,
  `attach_video(winId)`, `match_source()` (audio source of the loaded media, for identification).
</content>

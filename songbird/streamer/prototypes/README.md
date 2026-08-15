# UI prototypes

A sandbox for trying different UI designs **without touching the working app**.

## The layout
- `../link-stream.py` — the frozen, complete reference app. Don't edit it.
- `../engine.py` — the shared backend (player, yt-dlp, waveform, seeking, looping).
  All the plumbing lives here so each design file stays thin (just the look + layout).
- `design_b.py` — the current UI: video built on `engine.py`.

## Run a design
```bash
cd songbird-archive-streamer
.venv/bin/python prototypes/design_b.py
```

## Try a new design
1. Copy the baseline:  `cp prototypes/design_b.py prototypes/design_x.py`
2. Edit `design_x.py` — it's all UI: window layout, the `Timeline` drawing (`paintEvent`),
   colors/sizes, the controls row, the video frame. Change whatever you like.
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
  `attach_video(winId)`.

Once you settle on a design, we can fold it back into a single file to retire the split.
</content>

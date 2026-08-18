# Contract: GUI ↔ Identify Worker

Transport: the GUI spawns `.venv/bin/python songbird/streamer/identify_worker.py` via `QProcess` and
exchanges **newline-delimited JSON** — one request object per line on the worker's stdin, one result
object per line on the worker's stdout. The worker stays alive across many requests (warm model).

## Request (stdin, one line)

```json
{"id": 1, "src": "/path/or/https://page.url", "is_url": true, "config": "cap"}
```

- `is_url=true` → worker resolves fresh best-audio with yt-dlp (temp file) before matching.
- `config` ∈ {`cap`, `full`}.

## Result (stdout, one line)

Success:
```json
{"id": 1, "ok": true, "song": "Out the Door", "artist": "Congress the Band", "apple_url": "...", "elapsed": 7.4}
```
No match:
```json
{"id": 1, "ok": true, "song": null, "artist": null, "apple_url": null, "elapsed": 6.9}
```
Failure:
```json
{"id": 1, "ok": false, "error": "download failed: HTTP 410", "elapsed": 2.1}
```

## Lifecycle & failure semantics

- **Warm-up**: model loads lazily on the first request; later requests skip the load.
- **Crash**: if the worker exits abnormally (`QProcess::CrashExit`) the GUI shows an error, marks the
  worker dead, and re-spawns it on the next Identify. The GUI never crashes with it.
- **Timeout**: a GUI-side watchdog (e.g. ~180 s) cancels a stuck request and reports failure.
- **Ordering**: one in-flight request at a time (Identify buttons disabled while matching), so `id`
  correlation is advisory.
- **stderr**: worker diagnostics (VLC/torch noise) go to stderr and are ignored by the protocol parser.

## Output-contract note

Only song/artist + resolved Apple/Spotify links reach the user. `apple_url`, `elapsed`, and any
candidate ranking are internal (benchmark/diagnostics), never rendered in the app.

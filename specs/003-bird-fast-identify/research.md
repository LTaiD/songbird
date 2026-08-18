# Research: crash-proof, faster identification

## Decision 1 — Isolate matching in a worker process (not a thread)

**Decision**: Run identification in a separate long-lived Python process launched and driven by Qt's
`QProcess`; communicate over stdin/stdout with one JSON object per line.

**Rationale**: The crash is a native segfault (torch/MuQ + faiss + librosa/numba loaded together;
`index.py` imports torch then faiss — the classic macOS OpenMP double-load hazard). A native crash in
the same process kills the GUI regardless of Python `try/except`. A separate process contains the
crash: the GUI observes `finished(exitCode, CrashExit)` and stays alive. `QProcess` integrates with
the Qt event loop, so no Python thread runs native code alongside the UI. Long-lived → the MuQ model
is loaded once and reused (warm), which is also the biggest repeat-latency win.

**Alternatives considered**:
- *Daemon thread (current)* — rejected: cannot survive a native segfault; also fights the GIL/Qt.
- *`multiprocessing`* — workable but heavier to wire into the Qt event loop than `QProcess`.
- *In-process OpenMP fix (`KMP_DUPLICATE_LIB_OK`, import ordering)* — masks, not fixes; fragile across
  environments; still crashes on any other native fault.

## Decision 2 — Fix HTTP 403 by re-resolving fresh audio at match time

**Decision**: `engine.match_source()` returns the **original page URL** the user pasted (stored in
`load()`), not the expiring resolved stream URL. The worker, given a URL, uses yt-dlp to fetch fresh
best-audio at match time (temp file), then matches that. File uploads pass through unchanged.

**Rationale**: yt-dlp media URLs are short-lived and IP-locked; by identify-time they 403 (exactly the
reported error). Re-resolving at match time always yields a working source. Downloading audio also
sidesteps ffmpeg-over-HLS quirks.

**Alternatives considered**:
- *Re-resolve just a fresh stream URL (no download)* — usually works but still streams over the
  network into ffmpeg; downloading a temp file is the most robust and is what the benchmark needs anyway.
- *Reuse the already-downloaded waveform from playback* — the engine only keeps coarse peaks, not
  match-quality audio; rejected.

## Decision 3 — Batch the MuQ forward passes

**Decision**: Add `embed.embed_windows(wavs)` that stacks equal-length windows into one `(B, win)`
tensor and runs a single `no_grad` forward, mean-pooling + L2-normalizing per row. `windowing.embed_all`
uses it. The final short/ragged window (when the track isn't a whole multiple) is embedded on its own.

**Rationale**: The dominant cost is ~47 sequential model calls for a 4-min song; one batched call
amortizes Python/dispatch overhead and lets BLAS parallelize. Numerically equivalent to the loop
(same per-window mean-pool), so accuracy is unchanged — verified by the module self-check.

**Alternatives considered**:
- *Smaller/quantized model or ONNX* — changes embeddings, requires rebuilding the 1102-song index;
  out of scope and risks accuracy.
- *Larger hop only* — reduces windows but also reduces votes; the cap config already explores this.

## Decision 4 — Two configs, benchmarked blind

**Decision**: `matcher.match(..., max_seconds=None, recall_k=12)`. **cap** = `max_seconds≈90`,
`recall_k=5`; **full** = `max_seconds=None`, `recall_k=12`. Benchmark downloads each of the 3 URLs to a
neutrally-named temp file and runs both configs, recording elapsed, prediction, correctness, top-k.

**Rationale**: The user wants evidence to choose. Capping trims both MuQ passes and rerank fetches;
full preserves all-window aggregation (constitution P9). Blind (neutral filenames, no title passed)
keeps the accuracy numbers honest — the model is audio-only, so this is a procedural safeguard.

**Alternatives considered**:
- *Pick one config up front* — rejected; the user explicitly asked to benchmark both.

## Decision 5 — Flying-bird header via QPainterPath fill test

**Decision**: Build a stylized wings-spread bird as a `QPainterPath` scaled to the header field rect;
for each grid cell whose center is inside the path, draw a dense palette square; keep the existing
seeded-random sparse squares beyond the body so the bird dissolves into the field.

**Rationale**: A path fill test gives a clean, resolution-independent silhouette with little code and
reuses the current dense→sparse aesthetic. No image asset dependency (self-contained).

**Alternatives considered**:
- *Sample the supplied PNG into a bitmap mask* — the PNG is a perched bird; the user asked for a flying
  bird, so a hand-shaped path is more faithful and avoids bundling an asset.
- *Animated assembly* — deferred; spec says static this iteration.

## Open inputs (gate the benchmark only)

- Ground-truth (song, artist) for each of the 3 URLs.
- Congress the Band – "Out the Door" studio reference audio to add to `reference/` + rebuild catalog.

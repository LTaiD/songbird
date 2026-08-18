# Feature Specification: Flying-bird header + crash-proof, faster identification

**Feature Branch**: `003-bird-fast-identify`

**Created**: 2026-08-16

**Status**: Draft

**Input**: User description: "Flying-bird header art + crash-proof, faster song identification for the Songbird streamer" (three parts: flying-bird header, worker-isolated + 403-fixed Identify, batched/two-config speedups benchmarked blind on 3 songs).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Identify a song without crashing the app (Priority: P1)

A user loads a live/cover recording (a pasted link or an uploaded file) and clicks **Identify Song**.
The app returns the song's name, artist, and streaming links — and never crashes, even if the model
or a native library fails internally.

**Why this priority**: Today identification crashes the whole GUI (a native segfault) and a loaded
link usually fails with an HTTP 403 (expired stream URL). This is the core value of the product and
is currently broken; nothing else matters if the app dies on use.

**Independent Test**: Load a link, click Identify → a result (or a clean "no match"/error message)
appears and the window stays open and usable. Kill the identify worker mid-run → the app reports a
failure and remains alive; a second Identify still works.

**Acceptance Scenarios**:

1. **Given** a loaded YouTube/TikTok link whose earlier playback stream has expired, **When** the
   user clicks Identify Song, **Then** identification uses freshly re-resolved audio and returns a
   result without an HTTP 403 failure.
2. **Given** an identification is running, **When** the underlying matching process crashes, **Then**
   the GUI shows an error message and stays responsive (no crash), and a subsequent Identify succeeds.
3. **Given** a local audio/video file, **When** the user uploads it and clicks Identify, **Then** a
   result or a clean "no match" message appears.

---

### User Story 2 - Faster identification (Priority: P2)

A user expects identification to finish in a reasonable time rather than minutes of frozen waiting.

**Why this priority**: Identification is "correct but slow" (many sequential model passes on CPU).
Speed is a major usability gap but secondary to not crashing.

**Independent Test**: Identify the same recording before and after; measure wall-clock time; confirm
a substantial reduction with equal or comparable correctness.

**Acceptance Scenarios**:

1. **Given** a ~4-minute recording, **When** the user identifies it, **Then** the result returns
   meaningfully faster than the current sequential-per-window baseline.
2. **Given** two speed configurations (a capped representative slice and a full-track pass), **When**
   both are benchmarked on the same recordings, **Then** their speed and accuracy are reported so a
   default can be chosen on evidence.

---

### User Story 3 - Flying-bird header art (Priority: P3)

A user opening the app sees the scattered squares beneath the "songbird" wordmark arranged as a
wings-spread flying bird that dissolves into a sparse square field to the right.

**Why this priority**: Visual polish; independent of the identification fixes and lowest risk.

**Independent Test**: Launch the app; the header reads as a flying bird made of squares, trailing
off into scattered squares. No functional dependency on identification.

**Acceptance Scenarios**:

1. **Given** the app is launched, **When** the header renders, **Then** a recognizable wings-spread
   bird silhouette is formed by dense squares, fading into the existing sparse scatter.

---

### Edge Cases

- Loaded link's stream has expired → re-resolve fresh audio; if the source is truly unavailable,
  show a clean error, not a crash.
- Identify worker dies (segfault, OOM, killed) → GUI reports failure, stays alive, respawns on next use.
- Identification takes too long / hangs → a watchdog times it out and reports a failure.
- Reference catalog missing the true song → returns a wrong or "no match" result (expected; not a crash).
- Benchmark query title/filename could leak the answer → benchmark must be blind (neutral names, no title passed).
- Congress the Band – "Out the Door" is absent from the catalog → must be added before it can match.
- The fallback shell UI must keep working after these changes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The app MUST identify a song from an uploaded file or a pasted link and return song
  name, artist, and streaming links, or a clear "no match" message.
- **FR-002**: Identification MUST run isolated from the GUI so that a failure in the matching code
  (including native crashes) cannot terminate or freeze the application.
- **FR-003**: On an identification-process failure or timeout, the app MUST report the failure and
  remain usable, and MUST be able to identify again afterward.
- **FR-004**: Identifying a previously loaded link MUST obtain fresh audio at identify-time so that an
  expired/blocked playback URL (HTTP 403) does not cause failure.
- **FR-005**: Identification MUST be materially faster than the current one-window-at-a-time baseline,
  by processing recording windows together rather than strictly sequentially.
- **FR-006**: The system MUST provide two identification configurations — a capped representative
  slice and a full-track pass — selectable for benchmarking.
- **FR-007**: A benchmark MUST measure both configurations on the same set of recordings and report
  per-recording and aggregate speed and correctness.
- **FR-008**: The benchmark MUST be blind: no song title or artist may be supplied to the identifier
  or embedded in query filenames; predictions derive solely from audio matched against the catalog.
- **FR-009**: The reference catalog MUST include the studio reference for "Congress the Band – Out the
  Door" before it can be identified (it is currently absent).
- **FR-010**: The header art MUST render the square field as a wings-spread flying bird dissolving
  into a sparse square scatter.
- **FR-011**: The existing fallback (shell) UI MUST continue to launch and function after these changes.
- **FR-012**: Model/setup cost SHOULD be paid once and reused across repeated identifications within a
  session rather than repeated per request.

### Key Entities *(include if feature involves data)*

- **Recording (query)**: user-supplied audio/video (file or link) to identify; no trusted metadata.
- **Catalog entry (reference)**: a studio track (song, artist, links) the query is matched against.
- **Identification result**: predicted song + artist + streaming links, or "no match".
- **Benchmark record**: per recording × configuration — elapsed time, prediction, correct/incorrect,
  and candidate ranking.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero app crashes across identification runs, including when the matching process is
  killed mid-run (the window stays open and can identify again).
- **SC-002**: Identifying a loaded link succeeds without an HTTP 403 failure in normal conditions.
- **SC-003**: Identification of a ~4-minute recording is at least ~3× faster than the current
  sequential baseline (target; actual reported by the benchmark).
- **SC-004**: The benchmark reports speed and accuracy for both configurations on all 3 test songs,
  enabling an evidence-based default choice.
- **SC-005**: The benchmark is verifiably blind — query filenames carry no title/artist and no title
  is passed to the identifier.
- **SC-006**: On launch, a viewer recognizes the header art as a flying bird.
- **SC-007**: The fallback shell UI still launches and identifies after the changes.

## Assumptions

- CPU-only inference (no GPU); the existing pretrained model + retrieval pipeline is reused, not
  retrained.
- The 3 benchmark recordings are the provided YouTube links; the user supplies each one's ground-truth
  song/artist and the missing Congress studio reference audio before the benchmark runs.
- A representative ~90-second slice is an acceptable default cap; the benchmark validates it against
  the full-track pass.
- "Blind" means no trusted query metadata; the audio model already ignores tags, so the safeguard is
  procedural (neutral filenames, no title passed).
- The header art is static (no animation) for this iteration.
- Fixing the loaded-link 403 is done by re-resolving fresh audio at identify-time; local file uploads
  are unaffected.

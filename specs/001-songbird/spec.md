# Feature Specification: Songbird — Live-Recording → Studio-Original Matcher

**Feature Branch**: `001-songbird`

**Created**: 2026-08-14

**Status**: Draft

**Input**: Link a live recording of a song to its studio original and return where to listen to it.

## User Scenarios & Testing

### User Story 1 - Identify a studio original from a live upload (Priority: P1)

A user has an audio or video file of a live performance. They upload it in the streamer and get back the studio song's name, artist, and links to hear the studio version on Apple Music and Spotify.

**Why this priority**: This is the whole product. Without it there is nothing.

**Independent Test**: Build a small reference index, feed a live clip of one indexed song to the matcher, confirm it returns that song's name and artist and two valid streaming links.

**Acceptance Scenarios**:

1. **Given** a reference index containing the studio song, **When** the user uploads a live recording of it, **Then** the system returns the correct song name, artist, Apple Music link, and Spotify link — and nothing else.
2. **Given** a live recording whose studio song is NOT in the index, **When** matched, **Then** the system returns its best available candidate (no crash, no extra fields).

### User Story 2 - Identify from a YouTube link (Priority: P2)

The streamer already loads YouTube URLs. The user loads a live performance URL and matches it without downloading a file first.

**Why this priority**: Reuses the existing streamer input path; high value, low added cost.

**Independent Test**: Load a YouTube URL of an indexed song, trigger match, confirm the four fields return.

**Acceptance Scenarios**:

1. **Given** a loaded YouTube performance, **When** the user triggers a match, **Then** the four contract fields are shown.

### User Story 3 - Add a new studio song by insertion (Priority: P3)

The operator drops a new studio track + metadata into the reference folder and rebuilds the index; the new song becomes matchable with no model retraining.

**Why this priority**: The Shazam-like add-by-insertion property; operationally important but not needed for the first demo.

**Independent Test**: Add a track to `reference/`, rebuild, confirm it can be retrieved.

### Edge Cases

- Query shorter than one window → still embed the available audio as a single window.
- Query full of solos/no head melody → aggregation across windows carries the decision (never single-window).
- Video container (mp4/mov) → extract audio track before loading.
- Empty index → return a clear "no reference songs" state, not a crash.
- Same-artist confusion (live and studio share the performer) → deferred fix (supervised contrastive projection) added only if it appears.

## Requirements

### Functional Requirements

- **FR-001**: System MUST accept audio (mp3, wav, m4a) and video (mp4, mov) inputs, plus the existing YouTube URL path.
- **FR-002**: System MUST load/resample audio to 24 kHz mono; for video it MUST extract the audio track with ffmpeg first.
- **FR-003**: System MUST window audio into 10-second windows with a 5-second hop, and support a 20-second window option.
- **FR-004**: System MUST embed each window with MuQ on CPU, mean-pool over time, and L2-normalize.
- **FR-005**: System MUST store reference vectors in a FAISS `IndexFlatIP` with a parallel (song, artist) map, saved to and loaded from disk.
- **FR-006**: System MUST retrieve top-k per query window, apply temperature-weighted voting, aggregate scores across all windows, and take the argmax as the single prediction.
- **FR-007**: System MUST resolve a prediction to an Apple Music link and a Spotify link.
- **FR-008**: System MUST display EXACTLY the four contract fields and nothing else.
- **FR-009**: System MUST let the operator build the reference index from user-supplied studio audio + metadata without retraining.

### Key Entities

- **Reference window vector**: one L2-normalized MuQ embedding of a studio-song window; maps to (song, artist).
- **Query performance**: the uploaded/streamed live recording; produces many window vectors that vote.
- **Match result**: (song name, artist, Apple Music link, Spotify link).

## Success Criteria

### Measurable Outcomes

- **SC-001**: A live recording of an indexed song resolves to that song's studio identity (not the recording/video), reliably in the top candidate after performance-level aggregation for clear cases.
- **SC-002**: The user-facing output contains only the four contract fields — verifiable by inspection.
- **SC-003**: Adding a new studio song requires only inserting its embedding + metadata and rebuilding, with no model retraining.
- **SC-004**: All module self-checks pass.

## Assumptions

- The user supplies the studio reference corpus (audio + `reference/metadata.csv`).
- Non-commercial MuQ licensing is acceptable for this build.
- Streaming links are search-query URLs; no Apple/Spotify API credentials are used.
- CPU inference is slow but acceptable for the demo; reference set and windows are kept modest.

# Feature Specification: Localhost Web Frontend

**Feature Branch**: `004-web-frontend`

**Created**: 2026-08-18

**Status**: Draft

**Input**: User description: "Retire the PySide6 desktop GUI in favor of a localhost web app for song identification. Identify-only (no player): submit a pasted URL OR an uploaded/drag-dropped audio/video file, show a listening orb while identifying, return EXACTLY ONE result (song, artist, Apple/Spotify/TikTok links). Single-answer contract is immutable. Error toast on failure. No auth, no deploy, localhost only. Reuse the existing Python core unchanged; move the old GUI out of the repo."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Identify a song from a link (Priority: P1)

A person has a link to a live recording or a song (YouTube, TikTok, etc.). They paste the link, submit, and get back the one song it is — its name, artist, and where to hear the studio original.

**Why this priority**: This is the core value and the most common input. A live recording lives at a URL far more often than as a local file. Delivering just this is a viable product.

**Independent Test**: Paste a known URL, submit, and confirm a single result appears with a song name, an artist, and three working streaming links — without any file handling involved.

**Acceptance Scenarios**:

1. **Given** an empty form, **When** the user pastes a valid media URL and submits, **Then** a listening animation appears, and on completion exactly one result (song, artist, three links) is shown.
2. **Given** a result is displayed, **When** the user clicks the Apple / Spotify / TikTok link, **Then** the corresponding streaming search for that song opens.
3. **Given** a URL that cannot be resolved or identified, **When** the user submits it, **Then** an error message appears and the form becomes usable again with the input preserved.

---

### User Story 2 - Identify a song from a file (Priority: P2)

A person has an audio or video file of a performance. They drag it onto the page (or pick it), submit, and get the one matching song and its links.

**Why this priority**: Second most common input; extends the same flow to local media. Not required for an MVP but high value.

**Independent Test**: Drag a known audio file onto the drop zone, submit, and confirm the same single-result output as the URL path.

**Acceptance Scenarios**:

1. **Given** an empty form, **When** the user drops an audio/video file and submits, **Then** the listening animation appears and one result is shown on completion.
2. **Given** a file is selected, **When** the user submits, **Then** the file name is visible so they know what will be identified.

---

### Edge Cases

- The user submits with neither a URL nor a file → the submit control stays disabled / a hint is shown; no request is made.
- The user submits both a URL and a file → the URL takes precedence (single, unambiguous input to the identifier), stated in the UI.
- Identification takes a long time (CPU-bound model) → the listening animation persists and the form stays locked until a result or error returns; no duplicate submissions are possible.
- The URL is reachable but contains no identifiable music → an error message is shown, not a wrong-looking empty result.
- A second submission starts before the first returns → prevented; the submit control is disabled while a request is in flight.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST accept a single identification input as either a pasted media URL or an uploaded/drag-dropped audio or video file.
- **FR-002**: The system MUST require no live playback or streaming — a static URL or file is sufficient to identify.
- **FR-003**: The system MUST return and display EXACTLY ONE result per identification: song name, artist, and three streaming links (Apple Music, Spotify, TikTok). A ranked list or shortlist MUST NEVER be shown (immutable single-answer contract).
- **FR-004**: While an identification is in progress, the system MUST show a distinct "listening" animation and MUST prevent additional submissions until it resolves.
- **FR-005**: On failure (unresolvable input, no identifiable music, internal error), the system MUST show a clear, transient error message and re-enable the form without losing the user's input.
- **FR-006**: The three streaming links MUST each open a search/track destination for the identified song on the respective service.
- **FR-007**: The system MUST run entirely on localhost with no authentication, accounts, or external hosting.
- **FR-008**: The system MUST reuse the existing identification core unchanged; the web layer only adapts input/output and MUST NOT alter matching, indexing, or model behavior.
- **FR-009**: The retired desktop GUI MUST be removed from the project and MUST NOT be a dependency of the web app.

### Key Entities *(include if feature involves data)*

- **Identification request**: the user's single input — a URL string or an uploaded media file.
- **Identification result**: exactly one song identity — song name, artist, and the Apple/Spotify/TikTok links derived for it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can go from an empty page to a displayed result (or a clear error) in a single submit action, with no more than one input step.
- **SC-002**: Every successful identification shows exactly one song and exactly three working streaming links — never zero, never more than one song.
- **SC-003**: 100% of in-flight submissions block a second submission until they resolve (no duplicate requests possible from the UI).
- **SC-004**: Every failure path results in a visible error and a form the user can immediately retry with, with their input intact.
- **SC-005**: The application runs from a clean checkout on localhost with no account creation, external service sign-up, or deploy step.

## Assumptions

- Only one result is ever surfaced, even when the underlying matcher's confidence is low; near-miss wrong answers are an accepted property of the model, not a UI failure.
- URL precedence over file when both are provided keeps the identifier's input unambiguous.
- "Streaming links" are search/track destinations that require no API keys or user auth.
- Concurrency is single-user localhost; one identification at a time is acceptable.
- The old desktop GUI is preserved outside the repository as archive; this feature only requires its removal from the project, not its deletion.

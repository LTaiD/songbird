# Feature Specification: Composition-aware rerank + music-activity detection

**Feature Branch**: `002-rerank`

**Created**: 2026-08-15

**Status**: Draft

**Input**: The single-answer Top-1 is fragile at catalog scale — MuQ ranks by timbre, so the correct studio song lands in the top-few but loses #1 to sonically-adjacent tracks. Add a composition-aware rerank and trim non-music query intros.

## User Scenarios & Testing

### User Story 1 - Correct single answer on a real live recording (Priority: P1)
A user submits a live/cover recording. The system returns the correct studio song as its one answer, even when a different song merely *sounds* similar.

**Independent Test**: Match the MJ Lenderman live "She's Leaving You" against the 1102-song catalog; MuQ alone returns Wilco (#1) with the correct song #2; after rerank the correct song is #1.

**Acceptance Scenarios**:
1. **Given** a live recording whose studio original is indexed, **When** matched, **Then** the composition (chord progression) rerank promotes the correct song over timbre twins.
2. **Given** a cross-instrument cover (piano cover of a ragtime piece), **When** matched, **Then** the correct studio song remains #1.

### User Story 2 - Ignore non-music intros (Priority: P2)
A recording that opens with talking/tuning/silence before the music must not let that intro pollute the match.

**Independent Test**: On the Jelly Roll Morton "The Crave" video (spoken intro), the system detects music starting ~19 s in and matches on the music only.

### Edge Cases
- Distorted/loud live band scores low on harmonicity → trim by music *span* (first..last), never carve the body.
- No network at query time → rerank skipped, MuQ answer returned (graceful).
- Purely instrumental / generic progression → rerank may not separate; falls back to MuQ order.

## Requirements

### Functional Requirements
- **FR-001**: System MUST detect the music region(s) of a query and trim non-music intro/outro before matching.
- **FR-002**: System MUST recall top-K candidate songs with MuQ (existing gated retrieval).
- **FR-003**: System MUST rerank the top-K by a timbre-independent composition signal (chroma / chord-progression alignment, key-invariant via OTI, local Smith-Waterman alignment).
- **FR-004**: System MUST return exactly one answer (contract unchanged) and degrade to the MuQ answer if rerank is unavailable.
- **FR-005**: No new model/library/framework (numpy + librosa, both already present).

## Success Criteria
- **SC-001**: On the 3-query real benchmark the correct studio song is the single Top-1 (or strictly improves vs MuQ-only).
- **SC-002**: Music detection trims the spoken intro on the Crave video and keeps the full body of a distorted live recording.
- **SC-003**: No regression on the 20-song LOO benchmark from any adopted change.

## Assumptions
- Catalog references are 30 s iTunes previews (short chroma coverage; alignment is local/subsequence).
- Rerank fetches the top-K candidates' previews at query time (network); acceptable given MuQ embedding already dominates latency.
- Consensus reranking (temporal voting) was evaluated and **rejected** — the confusion is dense, not sparse; only an orthogonal signal (chroma) helps.

# Phase 1 Data Model: Localhost Web Frontend

No persistent storage is added. Two transient shapes cross the web boundary.

## IdentifyRequest (client → `POST /identify`, multipart/form-data)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `url` | string | one of url/file | A media page URL (YouTube/TikTok/etc.). If present, takes precedence over `file`. |
| `file` | file upload | one of url/file | An audio or video file. Written to a temp path, passed to `match()`, deleted after. |

Validation: at least one of `url` / `file` must be present, else `400`. The web core
(`songbird.audio.load`) already branches on URL vs. file/video extension, so the backend
passes the raw URL string or the temp file path straight through.

## IdentifyResult (`POST /identify` → client, application/json)

Success (`200`):

| Field | Type | Source |
|-------|------|--------|
| `song` | string | `match()[0]` |
| `artist` | string | `match()[1]` |
| `apple` | string (URL) | `links()[0]` (canonical iTunes URL when catalog has it, else search) |
| `spotify` | string (URL) | `links()[1]` (search URL) |
| `tiktok` | string (URL) | `links()[2]` (search URL) |

Exactly one result object — never a list (immutable single-answer contract, FR-003).

Error (`400` bad/again-usable input, `422` no identifiable music, `500` internal):

| Field | Type | Notes |
|-------|------|-------|
| `error` | string | Human-readable message shown in the toast; form re-enables. |

## Frontend UI state (in-memory only)

`idle → submitting (listening orb, form locked) → result | error → idle`

- `submitting` blocks a second submit (SC-003).
- `result` and `error` both return the form to a usable state with input preserved (FR-005).

# Contract: `POST /identify`

Localhost song-identification endpoint. Wraps `songbird.matcher.match()` +
`songbird.links.links()` with no core changes.

## Request

- **Method / path**: `POST /identify`
- **Content-Type**: `multipart/form-data`
- **Fields** (at least one required; `url` wins if both sent):
  - `url` — string, a media page URL.
  - `file` — an uploaded audio or video file.

## Behavior

1. If `url` present → `src = url`. Else if `file` present → save to temp path, `src = tmp`.
   Else → `400 {"error": "Provide a URL or a file."}`.
2. `result = match(src, data_dir="data/catalog", max_seconds=90, recall_k=5)`.
   (Bounded config for responsiveness — mirrors the old worker's `cap` mode.)
3. If `result is None` → `422 {"error": "No identifiable music found."}`.
4. Else `song, artist, apple = result`; `apple, spotify, tiktok = links(song, artist, apple)`;
   → `200` with the success body.
5. Any resolution/decode exception → `400 {"error": "<message>"}`; unexpected → `500`.
6. Temp upload file deleted in a `finally`.

## Responses

**200 OK**
```json
{
  "song": "She's Leaving You",
  "artist": "MJ Lenderman",
  "apple": "https://music.apple.com/...",
  "spotify": "https://open.spotify.com/search/...",
  "tiktok": "https://www.tiktok.com/search?q=..."
}
```

**400 / 422 / 500**
```json
{ "error": "No identifiable music found." }
```

## Invariants

- Exactly one result object on success — never an array, never a shortlist.
- No scores, embeddings, video IDs, or timestamps in any response (constitution §8).
- Concurrency: one identification at a time is acceptable (single-user localhost).

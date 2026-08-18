# Data Model

No database changes. Entities are in-memory/IPC payloads and existing on-disk artifacts.

## IdentifyRequest (GUI → worker, one JSON line)

| Field    | Type   | Notes                                                        |
|----------|--------|-------------------------------------------------------------|
| `src`    | string | file path (upload) or page URL (loaded link)                |
| `is_url` | bool   | true → worker re-resolves fresh audio via yt-dlp            |
| `config` | string | `"cap"` or `"full"`                                          |
| `id`     | int    | optional correlation id                                     |

## IdentifyResult (worker → GUI, one JSON line)

| Field       | Type            | Notes                                          |
|-------------|-----------------|------------------------------------------------|
| `ok`        | bool            | success flag                                   |
| `song`      | string \| null  | present when `ok` and a match exists           |
| `artist`    | string \| null  | present when `ok` and a match exists           |
| `apple_url` | string \| null  | Apple search seed used for link resolution     |
| `error`     | string \| null  | present when `ok` is false                     |
| `elapsed`   | number          | seconds spent matching                         |

Note: user-facing output stays song/artist + Apple/Spotify links (existing `links.resolve`). `apple_url`
here is an internal seed, not shown raw.

## BenchmarkRecord (benchmark script, per URL × config)

| Field      | Type    | Notes                                             |
|------------|---------|---------------------------------------------------|
| `url`      | string  | test source                                       |
| `config`   | string  | `cap` \| `full`                                   |
| `elapsed`  | number  | seconds                                           |
| `pred`     | (song, artist) \| null | prediction                          |
| `correct`  | bool    | pred == ground-truth                              |
| `topk`     | list    | candidate (song, artist) ranking (internal only)  |

Aggregates per config: accuracy % and mean/median latency.

## Existing artifacts (unchanged shape)

- **FAISS index** `data/catalog/index.faiss` + **map** `data/catalog/index_map.json` (rows of
  `[song, artist, apple_url?]`). Adding the Congress reference appends rows via the normal build.
- **Engine state**: adds `self._page_url` (string) set in `load()`; `match_source()` returns it.

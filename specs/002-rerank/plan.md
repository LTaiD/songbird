# Implementation Plan: 002-rerank

**Spec**: `./spec.md` · **Constitution**: `../../.specify/memory/constitution.md`

## Technical context
- numpy + librosa only (already installed). No new model/library.
- Retrieve-then-rerank over MuQ's existing catalog embeddings; rerank fetches top-K candidate previews from the free iTunes API at query time.

## Architecture
```
query audio
  → music-activity trim (songbird/activity.py)  [span first..last music]
  → MuQ windows → gated recall top-K songs (matcher.match_topk)
  → chroma rerank (songbird/rerank.py): per candidate, iTunes preview →
       chroma_cqt → OTI (12 shifts) → local SW alignment vs query chroma
  → single answer (highest alignment) + canonical Apple link
```

## Key decisions
- **Music trim = span**, not per-frame gating — robust to loud/distorted mixes (which score low on chroma clarity) while still cutting spoken intros.
- **Aligner = local Smith-Waterman** over OTI-transposed chroma cosine (diagonal + vertical-gap, row-vectorized in numpy). Subsequence-DTW was tried and is *worse* (forced full alignment); SW is the working choice.
- **Consensus rerank rejected** — no formulation beat the exp baseline on LOO; the timbre confusion is dense across the timeline, so reweighting the same MuQ scores can't fix it.
- **Graceful fallback**: rerank wrapped in try/except; on any failure the MuQ Top-1 stands.

## Files
- `songbird/activity.py` (music detection), `songbird/rerank.py` (chroma align + iTunes preview fetch), `songbird/matcher.py` (`match_topk` recall + `match()` pipeline), reuse `audio/embed/windowing/index`.

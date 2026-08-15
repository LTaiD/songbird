# Tasks: 002-rerank

- [x] T001 `songbird/activity.py` — music-activity detection (librosa: RMS + HPSS harmonic fraction + chroma peakiness). `music_regions`, `music_span`, `trim_to_music`. Self-check + real check (trims Crave intro at 19s, keeps full SLY).
- [x] T002 Test data — add `Here/Pavement` + `The Crave/Jelly Roll Morton` to catalog (`build_catalog --add`); fetch query recordings (SLY live, The Crave). *Pavement cover video is DRM-locked on YouTube — un-fetchable.*
- [x] T003 Consensus rerank — implement 4 formulations, evaluate on LOO(56)+real. **Rejected** (none beat exp baseline).
- [x] T004 `songbird/rerank.py` — chroma_seq + OTI + row-vectorized SW `align_score`; `chroma_rerank(query_wav, candidates)` with iTunes preview fetch. Self-check.
- [x] T005 Wire into `matcher.match()` — trim → MuQ `match_topk` → chroma rerank → single answer; network-gated fallback. `match_topk` added.
- [ ] T006 Verify — self-checks pass; end-to-end `match()` returns correct song for SLY + Crave; report honestly (2 real queries; Pavement cover blocked).
- [ ] T007 (deferred) Precompute a catalog chroma store to drop query-time preview fetches, if latency matters.

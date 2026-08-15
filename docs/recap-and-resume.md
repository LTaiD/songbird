# Songbird — Recap and Resume Material

Part 1 (the recap) uses Simplified Technical English (ASD-STE 100): short
sentences, active voice, simple tenses, and one idea per sentence. Part 2 (resume
material) uses the STAR method and plain text for applicant tracking systems (ATS).

---

## Part 1 — Project Recap (ASD-STE 100)

### What Songbird does

Songbird listens to a live recording or a cover of a song. It finds the studio
original. It gives you the song name, the artist, and links to play the song.

This is not like Shazam. Shazam matches the exact recording. A live version is a
different recording, so Shazam fails. Songbird matches the song, not the recording.

### What worked

- **Pretrained embeddings find the song.** Songbird uses MuQ. MuQ is a large
  neural network for music. MuQ turns each part of the audio into a vector. Songs
  that are the same have similar vectors. The correct song is almost always in the
  top 5 results.
- **FAISS makes the search fast.** FAISS holds all the song vectors. It finds the
  nearest vectors in a few milliseconds.
- **The free catalog works.** Songbird builds its song list from the Apple iTunes
  preview service. Each song uses a 30-second clip. The catalog has 1102 songs. It
  uses only 19 megabytes, because it keeps vectors and not audio.
- **The build can stop and start again.** The build saves its work every 10 songs.
  If it stops, you start it again. It continues from the last saved point.
- **Music detection removes talk and silence.** Some recordings start with talk or
  tuning. Songbird measures the harmonic content of the audio. It keeps only the
  part with music. On one test video, it correctly removed the first 19 seconds.
- **Chord reranking fixes the top result.** The MuQ result ranks songs by their
  sound. This is a problem, because two different songs can sound alike. Songbird
  adds a second step. This step compares the chord sequence, not the sound. It uses
  chroma features and a local alignment algorithm. The chord sequence is the same
  for the same song, even for a different band. This step moved the correct song to
  first place in all three cover tests.

### What did not work

- **One answer is not always correct.** MuQ ranks by sound. Two songs that sound
  alike can change places. For one live recording, MuQ put the wrong song first and
  the correct song second.
- **Contrastive training did not transfer.** The reference paper trains a small
  projection network. This network learned the training songs well. But it made the
  results worse for new songs. So Songbird does not use it.
- **Consensus reranking did not help.** This method counts agreement across the
  audio. It did not improve the results. The reason is clear: the wrong song agrees
  across the whole recording, not only in a few places. A count cannot fix this.

### Current status

- The full pipeline works from end to end. It runs on an Apple M2 laptop. It uses
  only free tools.
- The pipeline has these steps: load audio, remove non-music, make windows, embed
  with MuQ, search with FAISS, rerank with chord features, return one answer.
- Songbird returns one song, one artist, and links to Apple Music, Spotify, and
  TikTok. The answer format does not change.
- The chord reranking passed all three cover tests. This includes a cover by a
  different band. Songbird moved that correct song from rank 6 to rank 1.

### Known limits

- The tests use three songs. This is a small test set.
- The chord step downloads short clips of the top candidates during the search.
  This adds 6 to 20 seconds and needs the internet.
- The best answer is often correct, but not always. This is a hard problem.

### Next plans

1. **Store the chord features in the catalog.** This removes the download step
  during the search. The search becomes faster.
2. **Test with more songs and more covers.** A larger test set gives a true score.
3. **Add lyric matching for songs with clear vocals.** This gives a strong extra
  signal. It uses voice separation and speech-to-text. It stays quiet when the song
  has no vocals.
4. **Try a purpose-built cover-song model** (for example ByteCover). Check the
  license first. Use it to rerank or to replace MuQ.

---

## Part 2 — Resume Material (STAR method, ATS-ready)

Use one variation per application. Each variation uses the STAR method: Situation,
Task, Action, Result. The text is plain, with strong verbs, standard terms, and
numbers. Keep it as plain text for applicant tracking systems.

### Variation A — Machine Learning focus

**Songbird — Cross-Performance Music Recognition System | Independent Project**
Python, PyTorch, FAISS, NumPy, librosa

- **Situation:** Audio fingerprinting fails on live and cover recordings because
  they are different performances of the same composition.
- **Task:** Build a machine learning system that recognizes song identity across
  performances, running entirely on a laptop CPU with only free resources.
- **Action:** Designed a two-stage retrieve-then-rerank pipeline: extracted frozen
  embeddings from MuQ, a 300M-parameter self-supervised music transformer, and
  indexed 1,100+ songs in a FAISS inner-product vector index for approximate
  nearest-neighbor retrieval; built an automated, resumable data pipeline that
  embedded 30-second previews from a public API into a 19 MB index; ran controlled
  ablations (temperature, k, aggregation) and a leave-one-performance-out benchmark
  to reject overfitting heuristics; implemented and evaluated a supervised
  contrastive projection head and documented its open-set transfer failure.
- **Result:** Raised leave-one-performance-out Top-1 accuracy from 0.75 to 0.79
  with confidence gating; delivered a reproducible end-to-end demo on an M2 CPU with
  no paid services and honest, benchmarked negative results.

Keywords: machine learning, deep learning, PyTorch, self-supervised learning,
embeddings, vector search, FAISS, nearest neighbor, information retrieval, model
evaluation, benchmarking, ablation study, contrastive learning, data pipeline,
Python, NumPy, CPU inference.

### Variation B — Music / Audio (MIR) focus

**Songbird — Music Information Retrieval for Live and Cover Songs | Independent Project**
Python, librosa, FAISS, PyTorch, digital signal processing

- **Situation:** Recognizing the same song across different performers, keys,
  tempos, and arrangements is an open music information retrieval (MIR) problem.
- **Task:** Match a live or cover recording to its studio original using audio
  features that are invariant to timbre and performance.
- **Action:** Engineered an audio pipeline with librosa (24 kHz mono, 10-second
  windows) and MuQ embeddings for candidate retrieval; built a music-activity
  detector from RMS energy, harmonic-percussive separation, and chroma salience to
  trim spoken intros; implemented a version-identification reranker using chroma
  (pitch-class) features, optimal transposition for key invariance, and local
  Smith-Waterman alignment of chord progressions.
- **Result:** Correctly identified a cover by a different band, moving the studio
  original from rank 6 (timbre-based) to rank 1 (harmony-based); validated cross-
  performance matching on same-artist live, cross-instrument, and cross-artist
  covers.

Keywords: music information retrieval, MIR, audio signal processing, librosa,
chroma features, chord progression, cover song identification, source separation,
key invariance, sequence alignment, feature engineering, Python.

### Variation C — Creativity / Product focus

**Songbird — "Shazam for Live Music" Prototype | Independent Project**
Python, machine learning, rapid prototyping

- **Situation:** Existing music recognition apps cannot identify a song from a live
  show or a cover, which leaves a real user need unsolved.
- **Task:** Prototype a working product that names a song from any performance and
  returns where to listen, using only free and local resources.
- **Action:** Framed the problem as retrieve-then-rerank after diagnosing that
  sound-based models find the right song in the top few but rank it inconsistently;
  reused a public preview API to auto-build a catalog with zero manual data entry;
  invented a chord-progression reranking step to separate songs that merely sound
  alike; ran fast, honest experiments and discarded three approaches that did not
  improve accuracy.
- **Result:** Turned a fragile top-guess into the correct answer on every cover
  tested, including a full-band cover; produced a clear, end-to-end demo and a
  documented decision trail that shows judgment and resourcefulness.

Keywords: rapid prototyping, product thinking, problem framing, experimentation,
machine learning, resourcefulness, end-to-end system, iteration, evaluation.

### Variation D — Mixture (balanced)

**Songbird — Cross-Performance Song Recognition | Independent Project**
Python, PyTorch, FAISS, librosa

- **Situation:** Live and cover recordings are different performances, so audio
  fingerprinting cannot recognize them.
- **Task:** Build and evaluate an end-to-end machine learning system that identifies
  the underlying song, entirely on a laptop CPU with free tools.
- **Action:** Combined a self-supervised audio embedding model (MuQ) with FAISS
  nearest-neighbor retrieval over an auto-built 1,100-song catalog, then added a
  music information retrieval reranker (chroma chord-progression alignment) that is
  invariant to timbre and key; built a resumable data pipeline, ran a
  leave-one-performance-out benchmark, and rejected two heuristics and one training
  method with measured evidence.
- **Result:** Improved Top-1 selection on real cover queries, including a
  cross-artist cover moved from rank 6 to rank 1, and raised benchmark Top-1
  accuracy from 0.75 to 0.79, all reproducible on an M2 CPU.

Keywords: machine learning, PyTorch, embeddings, FAISS, information retrieval,
music information retrieval, evaluation, benchmarking, data pipeline, Python, CPU.

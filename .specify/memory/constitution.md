# Songbird Constitution

## Principles (non-negotiable)

1. **No code comments.** No file Songbird produces contains code comments.
2. **No version control by the agent.** No git commits, pushes, tags, or branch operations. The user owns all VCS.
3. **FAISS only for vector search.** No Qdrant, Chroma, pgvector, Pinecone, or any external vector database.
4. **MuQ on CPU.** MuQ runs with `device="cpu"`. No GPU is assumed.
5. **`songbird-archive-streamer` is untouchable source.** Never delete, edit, or move anything inside it. Work only on copies inside this repo.
6. **No `tipofmyear` code.** Do not install, clone, import, or copy code from the paper's repository. Use its findings only; write all code from scratch.
7. **No Gradio. No from-scratch Harmonic CNN.** The paper shows the Harmonic CNN scores below random; it is forbidden.
8. **Output contract is exact.** Per match, return exactly: song name, artist, Apple Music link, Spotify link. No video ID, timestamps, raw scores, embeddings, or waveform data in user-facing output.
9. **Performance-level decisions only.** Never decide song identity from a single window; always aggregate across all query windows.

## Accepted exceptions (user-confirmed 2026-08-14)

- MuQ (`OpenMuQ/MuQ-large-msd-iter`) is CC-BY-NC 4.0 (non-commercial). Accepted for this demo/research build.
- The reference corpus is user-supplied; the index is empty until studio audio + metadata are provided.
- Links are Apple/Spotify search-query URLs (no API keys).
- Spec Kit drives planning; the multi-agent oversight swarm is not used.

## Governance

These principles override convenience. Any deviation must be user-approved and recorded here.

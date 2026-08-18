import numpy as np
import torch
from muq import MuQ

MODEL_ID = "OpenMuQ/MuQ-large-msd-iter"

_MODEL = None


def _model():
    global _MODEL
    if _MODEL is None:
        _MODEL = MuQ.from_pretrained(MODEL_ID).to("cpu").eval()
    return _MODEL


def embed_window(wav):
    x = torch.from_numpy(np.asarray(wav, dtype=np.float32)).unsqueeze(0)
    with torch.no_grad():
        out = _model()(x, output_hidden_states=True)
    h = out.last_hidden_state.squeeze(0)
    v = h.mean(dim=0)
    v = v / v.norm(p=2).clamp_min(1e-12)
    return v.numpy().astype(np.float32)


def embed_windows(wavs, batch_size=8):
    vecs = []
    with torch.no_grad():
        for i in range(0, len(wavs), batch_size):
            chunk = [np.asarray(w, dtype=np.float32) for w in wavs[i:i + batch_size]]
            x = torch.from_numpy(np.stack(chunk))
            out = _model()(x, output_hidden_states=True)
            h = out.last_hidden_state
            v = h.mean(dim=1)
            v = v / v.norm(p=2, dim=1, keepdim=True).clamp_min(1e-12)
            vecs.append(v.numpy().astype(np.float32))
    return np.concatenate(vecs, axis=0).astype(np.float32)


def _demo():
    rng = np.random.default_rng(0)
    wav = (0.1 * rng.standard_normal(24000)).astype(np.float32)
    v = embed_window(wav)
    assert v.ndim == 1, v.shape
    assert abs(float(np.linalg.norm(v)) - 1.0) < 1e-3, np.linalg.norm(v)

    wav2 = (0.1 * rng.standard_normal(24000)).astype(np.float32)
    batch = embed_windows([wav, wav2], batch_size=1)
    batch2 = embed_windows([wav, wav2], batch_size=8)
    assert batch.shape == (2, v.shape[0]), batch.shape
    assert np.allclose(batch[0], v, atol=1e-4), float(np.abs(batch[0] - v).max())
    assert np.allclose(batch, batch2, atol=1e-4), "batch size changed the embedding"
    print("embed.py ok: D =", v.shape[0], "batched==per-window")


if __name__ == "__main__":
    _demo()

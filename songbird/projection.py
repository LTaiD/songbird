import os

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

PROJ_PATH = "data/projection.pt"
D_IN = 1024
D_OUT = 256


class Projection(nn.Module):
    def __init__(self, d_in=D_IN, d_hidden=512, d_out=D_OUT):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d_in, d_hidden), nn.ReLU(), nn.Linear(d_hidden, d_out))

    def forward(self, x):
        return F.normalize(self.net(x), dim=-1)


class Model(nn.Module):
    def __init__(self, n_songs, d_in=D_IN):
        super().__init__()
        self.proj = Projection(d_in)
        self.head = nn.Linear(D_OUT, n_songs)

    def forward(self, x):
        z = self.proj(x)
        return z, self.head(z)


def supcon_loss(z, song, perf, tau=0.1):
    b = z.shape[0]
    sim = z @ z.t() / tau
    eye = torch.eye(b, dtype=torch.bool, device=z.device)
    logits = sim.masked_fill(eye, -1e9)
    logits = logits - logits.max(dim=1, keepdim=True).values.detach()
    log_prob = logits - torch.log(torch.exp(logits).sum(dim=1, keepdim=True) + 1e-12)
    pos = (song[:, None] == song[None, :]) & (perf[:, None] != perf[None, :])
    pc = pos.sum(dim=1)
    valid = pc > 0
    if not valid.any():
        return z.sum() * 0.0
    per_anchor = -(log_prob * pos).sum(dim=1)[valid] / pc[valid]
    return per_anchor.mean()


def _sample(song, per_song, n_songs_b):
    songs = torch.unique(song)
    chosen = songs[torch.randperm(len(songs))[:n_songs_b]]
    idx = []
    for s in chosen:
        si = (song == s).nonzero(as_tuple=True)[0]
        idx.append(si[torch.randint(0, len(si), (per_song,))])
    return torch.cat(idx)


def train(npz_path="data/train_embeds.npz", epochs=400, lam=0.2, tau=0.1,
          lr=1e-3, n_songs_b=8, per_song=16, seed=0, out=PROJ_PATH, verbose=True):
    torch.manual_seed(seed)
    d = np.load(npz_path)
    X = torch.tensor(d["vectors"], dtype=torch.float32)
    song = torch.tensor(d["song_id"], dtype=torch.long)
    perf = torch.tensor(d["perf_id"], dtype=torch.long)
    n_songs = int(song.max()) + 1
    model = Model(n_songs, X.shape[1])
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    for e in range(epochs):
        idx = _sample(song, per_song, min(n_songs_b, n_songs))
        z, logits = model(X[idx])
        loss = F.cross_entropy(logits, song[idx]) + lam * supcon_loss(z, song[idx], perf[idx], tau)
        opt.zero_grad(); loss.backward(); opt.step()
        if verbose and (e % 100 == 0 or e == epochs - 1):
            print(f"epoch {e} loss {loss.item():.4f}")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    torch.save(model.proj.state_dict(), out)
    return out


_PROJ = None


def load_projection(path=PROJ_PATH, d_in=D_IN):
    global _PROJ
    if _PROJ is None:
        if not os.path.exists(path):
            return None
        m = Projection(d_in)
        m.load_state_dict(torch.load(path))
        m.eval()
        _PROJ = m
    return _PROJ


def project_matrix(vecs, path=PROJ_PATH):
    m = load_projection(path)
    if m is None:
        return np.asarray(vecs, dtype=np.float32)
    with torch.no_grad():
        z = m(torch.tensor(np.asarray(vecs, dtype=np.float32)))
    return z.numpy().astype(np.float32)


def _demo():
    import tempfile
    rng = np.random.default_rng(0)
    n_songs, n_perf, n_win, d = 6, 3, 20, 1024
    song_center = rng.standard_normal((n_songs, d))
    vecs, song_ids, perf_ids = [], [], []
    for s in range(n_songs):
        for p in range(n_perf):
            perf_bias = 2.0 * rng.standard_normal(d)
            w = song_center[s] + perf_bias + 0.3 * rng.standard_normal((n_win, d))
            vecs.append(w.astype(np.float32))
            song_ids += [s] * n_win
            perf_ids += [s * 10 + p] * n_win
    V = np.concatenate(vecs)
    V /= np.linalg.norm(V, axis=1, keepdims=True)
    d0 = tempfile.mkdtemp()
    np.savez(os.path.join(d0, "t.npz"), vectors=V,
             song_id=np.array(song_ids), perf_id=np.array(perf_ids))
    out = os.path.join(d0, "p.pt")
    train(os.path.join(d0, "t.npz"), epochs=300, out=out, verbose=False)

    def same_diff_cos(mat):
        s = np.array(song_ids); p = np.array(perf_ids)
        M = mat @ mat.T
        sd = M[(s[:, None] == s[None, :]) & (p[:, None] != p[None, :])].mean()
        cs = M[s[:, None] != s[None, :]].mean()
        return sd, cs

    raw_sd, raw_cs = same_diff_cos(V)
    Z = project_matrix(V, path=out)
    proj_sd, proj_cs = same_diff_cos(Z)
    print(f"raw:  same-song-diff-perf={raw_sd:.3f} cross-song={raw_cs:.3f} gap={raw_sd-raw_cs:.3f}")
    print(f"proj: same-song-diff-perf={proj_sd:.3f} cross-song={proj_cs:.3f} gap={proj_sd-proj_cs:.3f}")
    assert (proj_sd - proj_cs) > (raw_sd - raw_cs) + 0.05, "projection did not improve separation"
    print("projection.py ok")


if __name__ == "__main__":
    _demo()

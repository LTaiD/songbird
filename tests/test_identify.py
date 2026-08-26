from fastapi.testclient import TestClient

import server.app as appmod
from server.app import app

client = TestClient(app)


def test_success_shape_single_result(monkeypatch):
    monkeypatch.setattr(appmod, "_fetch_audio", lambda u: "/tmp/nonexistent-songbird.wav")
    monkeypatch.setattr(appmod, "match", lambda *a, **k: ("So What", "Miles Davis", ""))
    r = client.post("/identify", data={"url": "https://example.com/clip"})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"song", "artist", "apple", "spotify", "tiktok"}
    assert body["song"] == "So What" and body["artist"] == "Miles Davis"
    for key in ("apple", "spotify", "tiktok"):
        assert body[key].startswith("https://")


def test_no_identifiable_music_returns_error(monkeypatch):
    monkeypatch.setattr(appmod, "_fetch_audio", lambda u: "/tmp/nonexistent-songbird.wav")
    monkeypatch.setattr(appmod, "match", lambda *a, **k: None)
    r = client.post("/identify", data={"url": "https://example.com/clip"})
    assert r.status_code == 422
    assert "error" in r.json()


def test_missing_input_returns_error():
    r = client.post("/identify", data={})
    assert r.status_code == 400
    assert "error" in r.json()


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))

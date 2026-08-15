from urllib.parse import quote, quote_plus


def links(song, artist, apple_url=""):
    term = " ".join(p for p in (song, artist) if p).strip()
    apple = apple_url or "https://music.apple.com/us/search?term=" + quote_plus(term)
    spotify = "https://open.spotify.com/search/" + quote(term)
    tiktok = "https://www.tiktok.com/search?q=" + quote_plus(term)
    return apple, spotify, tiktok


def _demo():
    apple, spotify, tiktok = links("So What", "Miles Davis")
    assert apple.startswith("https://music.apple.com/us/search?term=")
    assert spotify.startswith("https://open.spotify.com/search/")
    assert tiktok.startswith("https://www.tiktok.com/search?q=")
    assert " " not in apple and " " not in spotify and " " not in tiktok
    assert "So%20What" in spotify or "So+What" in spotify
    assert "So+What" in tiktok or "So%20What" in tiktok
    a2, s2, t2 = links("Café", "Sœur & Cie")
    assert " " not in a2 and " " not in s2 and " " not in t2 and "%" in t2
    print("links.py ok:", apple, "|", spotify, "|", tiktok)


if __name__ == "__main__":
    _demo()

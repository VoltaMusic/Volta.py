# 🎧 VoltaLibPython

A lightweight Python client for the [Volta Music](https://volta-music.com) public API — automatic token refresh, typed exceptions, and a clean `client.get` / `client.post` / `client.put` / `client.delete` interface.

---

## ✨ Features

- 🔐 **Automatic token management** — fetches, refreshes, and persists your access token to disk. No manual token juggling.
- ♻️ **Silent retry on `401`** — if your token goes stale mid-request, the client refreshes it and retries once, transparently.
- 🧵 **Background auto-refresh** — a daemon thread keeps your token alive for the lifetime of the client.
- 🎯 **Typed exceptions** — catch `NotFoundError`, `AuthenticationError`, `RateLimitError`, etc. instead of parsing status codes yourself.
- 🧹 **Clean shutdown** — use it as a context manager and it saves remaining token time + closes its session automatically.
- 🔍 **Client-side search helpers** — filter your liked tracks/albums/artists/playlists by name without extra API calls.

---

## 📦 Installation

### From git

```bash
pip install git+https://github.com/VoltaMusic/Volta.py.git
```

### From a local build

```bash
python -m build
pip install dist/voltalib-1.0.1-py3-none-any.whl
```

---

## ⚙️ Config

Create a `.env` file at the root of your project:

```env
CLIENT_ID=volta_id_XXXXXXXXXXXXXXXXXX
CLIENT_SECRET=volta_sk_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

Get these from your Volta account, under **API Keys**. ⚠️ `CLIENT_SECRET` is shown only once at creation — copy it immediately.

---

## 🚀 Quick start

```python
from VoltaLibPython import VoltaClient

with VoltaClient() as client:
    tracks = client.get.library.tracks()
    print(tracks)
```

Using the context manager (`with ... as client:`) is the recommended way to use `VoltaClient` — it makes sure the background refresh thread stops cleanly and the remaining token time gets saved when you're done.

If you don't use a context manager, call `client.stop_background_refresh()` yourself before your program exits.

---

## 📖 Documentation

### 🟢 GET

#### Library — your personal collection (`client.get.library`)

```python
with VoltaClient() as client:
    client.get.library.tracks()                    # all liked tracks
    client.get.library.tracks(search="daft punk")   # filtered by title (case-insensitive)

    client.get.library.albums()
    client.get.library.albums(search="discovery")

    client.get.library.artists()
    client.get.library.artists(search="daft")       # filtered by name

    client.get.library.artist_albums("artist_id")
    client.get.library.artist_tracks("artist_id")

    client.get.library.playlists()                  # list all your playlists
    client.get.library.playlists(search="roadtrip")  # filtered by name
    client.get.library.playlists(id="playlist_id")   # a single playlist's details + tracks
```

> ⚠️ `search` and `id` are mutually exclusive on `playlists()` — passing both raises a `ValueError`.

#### Catalog — the global Volta catalog (`client.get.catalog`)

```python
with VoltaClient() as client:
    client.get.catalog.search("daft punk")   # global search: tracks, albums, artists, playlists

    client.get.catalog.artist("artist_id")   # artist details, top tracks, albums
    client.get.catalog.album("album_id")     # album details + tracks
    client.get.catalog.track("track_id")     # track metadata
    client.get.catalog.playlist("id")          # detail of a public playlist

    client.get.catalog.stream("track_id")    # track info and streaming URL
    client.get.catalog.home()                # home page sections (recommendations)
    client.get.catalog.state()               # current playback state
    client.get.catalog.me()                  # your profile (username, email, subscription)
```

#### Generic GET

```python
client.get.request("/api/v1/some/other/endpoint")
```

---

### 🟡 POST

#### Library & playlists (`client.post.library`)

```python
with VoltaClient() as client:
    client.post.library.track("track_id")                  # like a track (library:write)

    client.post.library.playlist("Roadtrip")               # create a playlist (playlists:write)
    client.post.library.playlist("Roadtrip", description="Summer 2026", is_public=False)

    client.post.library.playlist_track("playlist_id", "track_id")  # add a track to a playlist
```

#### Generic POST

```python
client.post.request("/api/v1/some/other/endpoint", {"key": "value"})
```

---

### 🟠 PUT

#### Library & playlists (`client.put.library`)

```python
with VoltaClient() as client:
    # Only the fields you pass are sent — the others are left unchanged.
    client.put.library.playlist("playlist_id", name="Roadtrip 2026")
    client.put.library.playlist("playlist_id", description="New description", is_public=True)

    # New order of the playlist's tracks
    client.put.library.reorder("playlist_id", ["track_3", "track_1", "track_2"])
```

> ⚠️ `put.library.playlist()` with no field to update raises a `ValueError` (no request is sent).

#### Generic PUT

```python
client.put.request("/api/v1/some/other/endpoint", {"key": "value"})
```

---

### 🔴 DELETE

#### Library & playlists (`client.delete.library`)

```python
with VoltaClient() as client:
    client.delete.library.track("track_id")        # unlike a track (library:write)
    client.delete.library.album("album_id")        # remove every track of an album from your library
    client.delete.library.artist("artist_id")      # unfollow an artist

    client.delete.library.playlist("playlist_id")                    # delete a playlist (playlists:write)
    client.delete.library.playlist_track("playlist_id", "track_id")  # remove a track from a playlist
```

#### Generic DELETE

```python
client.delete.request("/api/v1/some/other/endpoint")
```

---

## 🚨 Error handling

Every non-2xx response raises a typed exception (all inherit from `APIError`, which itself inherits from `VoltaAPIExceptions`):

| Exception | Raised on |
|---|---|
| `BadRequestError` | `400` |
| `AuthenticationError` | `401` — still invalid after an automatic refresh+retry |
| `ForbiddenError` | `403` |
| `NotFoundError` | `404` |
| `RateLimitError` | `429` |
| `ServerError` | `500`–`599` |
| `APIError` | any other non-2xx status code |

`ConfigurationError` (inherits from `VoltaAPIExceptions`, not `APIError`) is raised before any request when `CLIENT_ID` or `CLIENT_SECRET` is missing or empty.

Printing an exception gives a readable message, with the API's own explanation on the second line. It is also available as `e.detail`:

```
[400] Échec du rafraîchissement du token : Requête invalide
  -> client_id and client_secret are required
```

```python
from VoltaLibPython.exceptions import APIError, NotFoundError, VoltaAPIExceptions

try:
    client.get.catalog.track("unknown_id")
except NotFoundError:
    print("That track doesn't exist.")
except APIError as e:
    print(f"Something else went wrong: {e.status_code} — {e.detail}")
```

Catching `APIError` alone is enough if you don't need to distinguish error types. Catch `VoltaAPIExceptions` to also cover `ConfigurationError`.

---

## 🔑 Token lifecycle

- On first use, if no token file exists yet, the client fetches one via `client_credentials` and saves it to `config/token.json` (configurable via `token_file=` in `VoltaClient(...)`).
- A background thread refreshes the token shortly before it expires — no request ever waits on this.
- If the API rejects a request with `401` (token invalid sooner than expected), the client refreshes immediately and retries **once**, silently.
- On `stop_background_refresh()` (called automatically by the context manager, or manually), the real remaining time is written back to the token file — so restarting your program soon after doesn't waste a perfectly valid token.

---

## 🧪 Testing

The test suite uses `pytest` with a fully mocked HTTP layer — no real network calls, no real credentials needed.

```bash
pip install pytest
pytest
```

Tests are split by concern for readability:

```
tests/
├── conftest.py                # shared fixtures (fake HTTP session, client factory)
├── test_get_library.py        # tracks / albums / artists / artist_albums / artist_tracks / playlists
├── test_get_catalog.py        # search / artist / album / track / playlist / home / state / me
├── test_post.py               # library.track / playlist / playlist_track + generic request
├── test_put.py                # library.playlist / reorder + generic request
├── test_delete.py             # library.track / album / artist / playlist / playlist_track
└── test_client_lifecycle.py   # token loading/saving, context manager, thread-safety
```

---

## ⚠️ Known limitations

- `catalog.search(query)` inserts `query` directly into the URL (`?q={query}`) rather than through `params=`, so it isn't URL-encoded. Works fine for simple words, may break for queries with `&`, `#`, or other special characters.
- `library.tracks()/albums()/playlists()` with `search=` silently return an empty list if the API response isn't a list (rather than raising).

---

## 📄 License

*MIT License*

*Copyright (c) 2026-2027 Hugo Hennetin*

*Permission is hereby granted, free of charge, to any person obtaining a copy*
*of this software and associated documentation files (the "Software"), to deal*
*in the Software without restriction, including without limitation the rights*
*to use, copy, modify, merge, publish, distribute, sublicense, and/or sell*
*copies of the Software, and to permit persons to whom the Software is*
*furnished to do so, subject to the following conditions:*

*The above copyright notice and this permission notice shall be included in all*
*copies or substantial portions of the Software.*

*THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR*
*IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,*
*FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE*
*AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER*
*LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,*
*OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE*
*SOFTWARE.*
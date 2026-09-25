# 🎧 VoltaLibPython

A lightweight Python client for the [Volta Music](https://volta-music.com) public API — automatic token refresh, typed exceptions, and a clean `client.get` / `client.post` / `client.put` / `client.delete` interface.

---

## ✨ Features

- 🔐 **Automatic token management** — fetches, refreshes, and persists your access token to disk. No manual token juggling.
- ♻️ **Silent retry on `401`** — if your token goes stale mid-request, the client refreshes it and retries once, transparently.
- 🧵 **Background auto-refresh** — a daemon thread keeps your token alive for the lifetime of the client.
- 🎯 **Typed exceptions** — catch `NotFoundError`, `AuthenticationError`, `RateLimitError`, etc. instead of parsing status codes yourself.
- 🧹 **Clean shutdown** — use it as a context manager and it stops the refresh thread and closes its session automatically.
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
pip install dist/voltalib-1.4.0-py3-none-any.whl
```

---

## ⚙️ Config

Create a `.env` file at the root of your project:

```env
CLIENT_ID=volta_id_XXXXXXXXXXXXXXXXXX
CLIENT_SECRET=volta_sk_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

Get these from your Volta account, under **API Keys**. ⚠️ `CLIENT_SECRET` is shown only once at creation — copy it immediately.

You can also pass them directly, which takes priority over the environment (handy for notebooks, tests, or apps with their own secret store):

```python
client = VoltaClient(client_id="volta_id_...", client_secret="volta_sk_...")
```

---

## 🚀 Quick start

```python
from VoltaLibPython import VoltaClient

with VoltaClient() as client:
    tracks = client.get.library.tracks()
    print(tracks)
```

Using the context manager (`with ... as client:`) is the recommended way to use `VoltaClient` — it makes sure the background refresh thread stops and the HTTP session is closed when you're done.

If you don't use a context manager, call `client.close()` yourself when you're done: it stops the refresh thread and closes the HTTP session. If you forget, it is called automatically when your program exits.

To see a small loading spinner (on stderr) while a slow request is running, pass `show_progress=True`:

```python
with VoltaClient(show_progress=True) as client:
    ...
```

---

## 📖 Documentation

Full reference, one page per HTTP verb: [GET](docs/GET.md) · [POST](docs/POST.md) · [PUT](docs/PUT.md) · [DELETE](docs/DELETE.md)

### 🟢 GET

#### Library — your personal collection (`client.get.library`)

```python
with VoltaClient() as client:
    client.get.library.tracks()                    # all liked tracks
    client.get.library.tracks(search="daft punk")   # filtered by title (case- and accent-insensitive)

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
    client.get.catalog.me()                  # your profile: sub, name, preferred_username, nickname, picture (never the email)
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
    track = client.get.catalog.track("track_id")           # or any track from get.library.tracks() / search()
    client.post.library.track(track)                       # like a track (library:write)

    playlist = client.post.library.playlist("Roadtrip")    # create a playlist (playlists:write)
    client.post.library.playlist("Roadtrip", description="Summer 2026", is_public=False)

    client.post.library.playlist_track(playlist["id"], track)  # add a track to a playlist
```

> ⚠️ Adding a track needs the **whole track** (the dict returned by `get.library.tracks()`, `get.catalog.track()` or `search()`), not just its ID: the API also requires its name, artist and album. Passing only an ID raises an `InvalidArgumentError`.

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

The library never lets a raw `requests`, `json` or `OSError` exception escape: everything it raises inherits from `VoltaAPIExceptions`.

```
VoltaAPIExceptions
├── ConfigurationError           CLIENT_ID / CLIENT_SECRET missing or empty
├── InvalidArgumentError         bad argument, caught before any request (also a ValueError)
├── TokenStorageError            the token file can't be read or written
├── NetworkError                 no HTTP response at all
│   ├── ConnectionFailedError    server unreachable, DNS, connection refused, SSL
│   └── RequestTimeoutError      no response within the timeout
├── InvalidResponseError         2xx response that can't be used (not JSON, missing field, search= on a non-list)
└── APIError                     the API answered with an error status
    ├── BadRequestError          400
    ├── AuthenticationError      401 — still invalid after an automatic refresh+retry
    ├── ForbiddenError           403 — usually a scope missing on your API key
    ├── NotFoundError            404
    ├── ConflictError            409
    ├── UnprocessableEntityError 422 — request body rejected
    ├── RateLimitError           429 — see e.retry_after
    └── ServerError              500–599 (GET: after 3 automatic retries; POST / PUT / DELETE: never retried)
```

Any other non-2xx status raises a plain `APIError`.

Useful attributes:

| Exception | Attributes |
|---|---|
| `APIError` and subclasses | `status_code`, `detail` (the API's message), `response_text` |
| `RateLimitError` | `retry_after` — seconds to wait, from the `Retry-After` header (`None` if absent) |
| `NetworkError` and subclasses | `url` |
| `InvalidResponseError` | `response_text` |
| `TokenStorageError` | `path` |

The original low-level exception is always kept as `e.__cause__`.

Printing an exception gives a readable message, with the details on the next line:

```
[422] Request to https://api.volta-music.com/api/v1/library/playlists failed: Data rejected by the API
  -> name: field required
```

```python
from VoltaLibPython import (
    APIError, NetworkError, NotFoundError, RateLimitError, VoltaAPIExceptions,
)

try:
    client.get.catalog.track("unknown_id")
except NotFoundError:
    print("That track doesn't exist.")
except RateLimitError as e:
    print(f"Slow down, retry in {e.retry_after or 'a few'} seconds.")
except NetworkError:
    print("Can't reach Volta right now.")
except APIError as e:
    print(f"Something else went wrong: {e.status_code} — {e.detail}")
```

Catch `VoltaAPIExceptions` alone to handle every error the library can raise.

---

## 🔑 Token lifecycle

- On first use, if no token file exists yet, the client fetches one via `client_credentials` and saves it in your user cache folder: `%LOCALAPPDATA%\voltalib\` on Windows, `~/.cache/voltalib/` on Linux / macOS (or `$XDG_CACHE_HOME/voltalib/`). The file name depends on your `CLIENT_ID`, so two API keys never share a token, and the file is readable by your user only. Pass `token_file=` to `VoltaClient(...)` to use another path.
- A background thread refreshes the token shortly before it expires — no request ever waits on this.
- If the API rejects a request with `401` (token invalid sooner than expected), the client refreshes immediately and retries **once**, silently.
- The token file stores the absolute expiry time (`expires_at`, a Unix timestamp). A program restarted later reuses the token only if it is still valid, and fetches a new one otherwise — no wasted token, no stale token sent to the API.

---

## 🧪 Testing

The test suite uses `pytest` with a fully mocked HTTP layer — no real network calls, no real credentials needed.

```bash
pip install pytest
pytest
```

To run the lint and the tests on every supported Python version (3.10 → 3.13), like the CI does, use the matrix scripts. They need [uv](https://docs.astral.sh/uv/) (`pip install uv`), which downloads the missing Python versions and uses a temporary environment per version:

```bash
scripts/test_matrix.sh            # Linux / macOS / Git Bash
scripts/test_matrix.sh 3.12 3.13  # only some versions
```

```bat
scripts	est_matrix.bat           :: Windows (cmd / PowerShell)
scripts	est_matrix.bat 3.12 3.13
```

On GitHub, the same matrix runs on every push and pull request to `main`, and can be started by hand from the **Actions** tab (**Python application** → **Run workflow**).

Tests are split by concern for readability:

```
tests/
├── conftest.py                # shared fixtures (fake HTTP session, client factory)
├── test_get_library.py        # tracks / albums / artists / artist_albums / artist_tracks / playlists
├── test_get_catalog.py        # search / artist / album / track / playlist / home / state / me
├── test_post.py               # library.track / playlist / playlist_track + generic request
├── test_put.py                # library.playlist / reorder + generic request
├── test_delete.py             # library.track / album / artist / playlist / playlist_track
├── test_exceptions.py         # every exception: HTTP codes, network, invalid responses, token file, arguments
├── test_progress.py           # spinner: no added latency, stderr only, ASCII fallback
├── test_session.py            # retry policy: GET and token retried, POST / PUT / DELETE never
└── test_client_lifecycle.py   # token loading/saving, context manager, thread-safety, defaults
```

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
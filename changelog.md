# Changelog

All notable changes to VoltaLib, newest first. Each version lists every change made since the previous one.

Legend: `+` added · `~` changed / fixed · `-` removed

---

## Unreleased

```diff
+ [TEST] Tests for the background token refresh (success, failure retried in 30 s, no reschedule after close), token endpoint errors (401 / 400 / 5xx), token file write failures, 204 responses without a body, the spinner around requests, client.get.request(), every exception message and detail format, Retry-After parsing and spinner stream errors

~ [TEST] test_unwritable_token_file_raises_token_storage_error renamed to test_unreadable_...: it was testing the token file read, not the write
~ [DEV] _default_token_file() takes an os_name argument, so the Windows and Linux / macOS paths are both tested on every OS
```

## Ver 1.5.0 - Sep 25, 2026

```diff
+ [DOC] CONTRIBUTING.md: setup, checks, project layout, how to add an endpoint, conventions and release steps
+ [DEV] .pre-commit-config.yaml runs ruff and mypy before each commit (pre-commit install); pre-commit added to the dev extra
+ [FEAT] Every exception can be imported from the package root (from VoltaLibPython import NotFoundError), and VoltaLibPython.__version__ gives the installed version
+ [FEAT] VoltaClient(client_id=..., client_secret=...): credentials can be passed as arguments, and take priority over CLIENT_ID / CLIENT_SECRET from the environment
+ [FEAT] VoltaClient.close(): stops the refresh thread and closes the HTTP session (what the context manager does on exit)
+ [TEST] Track payload tests built from the real API shapes (library and catalog tracks)

~ [CHANGE] Importing the library no longer loads .env into os.environ: the .env file is only read when a VoltaClient is created without both credentials
~ [FIX] A client that is neither used with `with` nor closed by hand is now closed automatically when the program exits (atexit)
~ [FIX] The token file stores an absolute expiry time (expires_at) instead of a relative expires_in rewritten on exit: a token that expired while the program was stopped is no longer sent to the API (it used to cost a 401 and a retry). Old token files are still read, using the file's modification time
~ [CHANGE] close() / stop_background_refresh() no longer rewrite the token file
~ [CHANGE] The token file is saved by default in the user cache folder (%LOCALAPPDATA%\voltalib\ on Windows, ~/.cache/voltalib/ elsewhere) instead of config/token.json in the current directory, under a name that depends on CLIENT_ID. A new token is fetched once after upgrading; pass token_file="config/token.json" to keep the old location
~ [CHANGE] The token file is created readable by the current user only (0600)
~ [CHANGE] Every error message, log message and public docstring is now in English (they used to mix French and English)
~ [DEV] Endpoint classes share an _Endpoint base: routes are built with self._path("playlists", playlist_id, "tracks"), which encodes every segment, instead of repeated f-strings
~ [CI] The CI installs the package itself (pip install -e ".[dev]") instead of requirements.txt, lints with ruff instead of flake8 (whose second pass never failed the build), type-checks with mypy and reports test coverage; scripts/test_matrix.sh / .bat do the same
~ [BUILD] The dev extra adds pytest-cov, ruff, mypy and types-requests; ruff and mypy are configured in pyproject.toml
~ [FIX] library tracks() / albums() / artists() / playlists(): search and id are typed Optional[str]
~ [DOC] README: scripts\test_matrix.bat was printed with a tab instead of \t
~ [DEV] pytest settings moved from tests/pytest.ini (not read when pytest is run from the project root) to [tool.pytest.ini_options] in pyproject.toml; stale file names removed from test docstrings
~ [FIX] post.library.track() and post.library.playlist_track() now send the track object the API requires (id, name, artist, album, plus artist_id / album_id / cover_url / duration_ms when known) instead of {"track_id": ...}, which the API rejected with a 422
~ [CHANGE] post.library.track(track) and post.library.playlist_track(playlist_id, track) take the whole track dict (from get.library.tracks(), get.catalog.track() or search()), not just its ID; passing only an ID raises InvalidArgumentError with an explanation
~ [FIX] post.library.playlist(description=...) : the API ignores the description on creation, so it is now set right after with a PUT
~ [DOC] README and docs/POST.md: examples pass the whole track
```

## Ver 1.4.0 - Sep 24, 2026

```diff
+ [CI] Tests and lint run on Python 3.10, 3.11, 3.12 and 3.13 (matrix, fail-fast disabled) instead of 3.10 only
+ [BUILD] PyPI classifiers list the supported Python versions (3.10 to 3.13)
+ [CI] workflow_dispatch: the test matrix can be started by hand from the Actions tab
+ [DEV] scripts/test_matrix.sh and scripts/test_matrix.bat run the lint and the tests on every supported Python version with uv, like the CI
+ [DEV] .gitattributes keeps .sh files in LF and .bat files in CRLF
+ [DOC] docs/POST.md, docs/PUT.md and docs/DELETE.md

~ [CHANGE] requires-python raised from >=3.8 to >=3.10: the pinned dependencies (python-dotenv 1.2.3) need 3.10+ and the build backend (setuptools>=77) no longer installs on 3.8
~ [CI] actions/setup-python upgraded from v3 to v5
~ [CHANGE] The loading spinner is off by default (show_progress=False): pass show_progress=True to enable it. main.py keeps it on
~ [CHANGE] library search= raises InvalidResponseError when the API doesn't return a list, instead of silently returning an empty list
~ [FIX] docs/GET.md: client.git → client.get, albums() / artists() examples called tracks(), playlist() wrongly marked as not working, state() described the wrong data, stream() was missing, ValueError → InvalidArgumentError, scopes added
~ [DOC] README: links to the per-verb docs, show_progress, matrix scripts and manual CI run

- [DOC] README: last entry removed from Known limitations (search= on a non-list response)
```

## Ver 1.3.0 - Sep 24, 2026

```diff
+ [TEST] URL encoding tests for search / stream parameters and for IDs in every route

~ [FIX] catalog.search() and catalog.stream() send q / track_id through params=: queries with &, #, / or spaces are now URL-encoded instead of breaking the request
~ [FIX] IDs inserted in URL paths are encoded: an ID containing /, ? or # can no longer change the route that is called
~ [FIX] main.py only deletes its own results/ folder on exit, instead of every .json file in the current directory
~ [DOC] catalog.me() documents the fields the API actually returns (sub, name, preferred_username, nickname, picture): never the email or a subscription status

- [DOC] README: search URL-encoding removed from Known limitations
```

## Ver 1.2.0 - Sep 24, 2026

```diff
+ [TEST] tests/test_session.py covering the retry policy per method and per endpoint

~ [FIX] POST requests are no longer retried automatically on 500 / 502 / 503 / 504: a 5xx can arrive after the server already created the resource, and replaying it created duplicates (e.g. the same playlist 4 times)
~ [CHANGE] Automatic retries (3 attempts on 5xx) now only apply to GET requests and to the token endpoint, whose POST has no side effect
```

## Ver 1.1.3 - Sep 24, 2026

```diff
+ [BUILD] License declared as an SPDX expression (license = "MIT", license-files = ["LICENSE"]): removes the setuptools deprecation warning, builds would have stopped working on 2027-02-18
+ [BUILD] py.typed marker: type checkers (mypy, Pylance) now use the library's type hints
+ [BUILD] PyPI metadata: classifiers, keywords, Repository / Issues / Changelog links
+ [BUILD] Optional dev dependencies: pip install "VoltaLib[dev]" installs pytest and build

~ [FIX] Dependency python-dotenv declared directly instead of the dotenv wrapper package
~ [BUILD] Minimum versions for dependencies (requests>=2.25, urllib3>=1.26, python-dotenv>=0.19)
~ [BUILD] Only the VoltaLibPython package is picked up (explicit include instead of an exclude list with duplicates)
~ [BUILD] build-system requires setuptools>=77.0 only (wheel no longer needed)
~ [CHORE] requirements.txt pins python-dotenv instead of dotenv
```

## Ver 1.1.2 - Sep 24, 2026

```diff
+ [FEATURE] Spinner falls back to ASCII frames (| / - \) when the terminal can't display braille (e.g. Windows cp1252 console)
+ [TEST] tests/test_progress.py covering the spinner

~ [PERF] Spinner no longer adds ~100 ms to every request run in a terminal: the thread now wakes up instantly when the request ends instead of finishing a sleep()
~ [CHANGE] Spinner writes to stderr instead of stdout, so piped / redirected program output stays clean
~ [FIX] Spinner no longer crashes when stdout / stderr is None (pythonw) or closed
~ [FIX] Spinner only clears the line if it actually displayed something
```

## Ver 1.1.1 - Sep 24, 2026

```diff
+ [FEATURE] library search= is now accent-insensitive ("beyonce" finds "Beyoncé") and uses casefold() ("straße" finds "STRASSE")
+ [TEST] Shared search filter tests (accents, null fields, casefold)

~ [FIX] library search= no longer crashes when an item's title / name is null
~ [REFACTOR] tracks / albums / artists / playlists share a single _filter() helper instead of four copies
```

## Ver 1.1.0 - Sep 24, 2026

```diff
+ [FEATURE] Every error the library can hit is now a VoltaAPIExceptions subclass: no raw requests / json / OSError exception escapes anymore
+ [FEATURE] NetworkError, with ConnectionFailedError (unreachable, DNS, SSL) and RequestTimeoutError, instead of raw requests exceptions
+ [FEATURE] InvalidResponseError when the token endpoint answers 2xx with non-JSON or without access_token / expires_in
+ [FEATURE] TokenStorageError when the token file can't be read or written
+ [FEATURE] InvalidArgumentError (also a ValueError) for bad arguments caught before any request
+ [FEATURE] ConflictError (409) and UnprocessableEntityError (422)
+ [FEATURE] RateLimitError.retry_after, read from the Retry-After header
+ [TEST] tests/test_exceptions.py covering every exception
+ [DOC] README: full exception hierarchy and attributes

~ [FIX] A 5xx that persists after the automatic retries raises ServerError with the API's message instead of a raw requests RetryError
~ [FIX] A corrupted or incomplete token file no longer crashes the client: a new token is requested
~ [CHANGE] 422 validation details are shown as "field : message" instead of a raw Python list
~ [REFACTOR] GET / POST / PUT / DELETE share a single _request() method
```

## Ver 1.0.1 - Sep 24, 2026

```diff
+ [CI] Publish workflow cleans dist/ and build/ before building, then checks dist/ holds exactly one wheel and one tarball

~ [DOC] README: install from a local build (python -m build) instead of a committed wheel
~ [CI] Publish workflow comments rewritten in French

- [BUILD] dist/ no longer tracked in git (added to .gitignore)
```

## Ver 1.0.0 - Sep 24, 2026

```diff
+ [FEATURE] client.post.library: track(track_id), playlist(name, description, is_public), playlist_track(playlist_id, track_id)
+ [FEATURE] client.put.library: playlist(playlist_id, name, description, is_public) (only given fields are sent), reorder(playlist_id, track_ids)
+ [FEATURE] client.delete.library: track, album, artist, playlist, playlist_track
+ [TEST] Tests for every new POST / PUT / DELETE method
+ [DOC] README: POST / PUT / DELETE sections
+ [BUILD] dist/ 1.0.0 wheel and tarball

~ [DOC] README install command points to 1.0.0

- [REMOVED] client.post.track(data) and client.delete.track(id): use client.post.library.track(track_id) / client.delete.library.track(track_id)
```

## Ver 0.9.1 - Sep 23, 2026

```diff
+ [TEST] Missing credentials raise ConfigurationError without any network call
+ [BUILD] dist/ 0.9.1 wheel and tarball

~ [FIX] Tests no longer depend on the local .env: an autouse fixture provides fake CLIENT_ID / CLIENT_SECRET (20 tests failed in CI)
~ [DOC] README install command points to 0.9.1
```

## Ver 0.9.0 - Sep 23, 2026

```diff
+ [FEATURE] Readable error messages: "[status] context : reason" followed by the API's detail message instead of raw JSON
+ [FEATURE] APIError.detail: error message extracted from the API response (detail / message / error fields)
+ [FEATURE] New exceptions: BadRequestError (400), ForbiddenError (403), ConfigurationError (missing CLIENT_ID / CLIENT_SECRET)
+ [FEATURE] CLIENT_ID and CLIENT_SECRET checked before requesting a token
+ [FEATURE] main.py prints library errors without a traceback (full traceback kept in the log file)
+ [FEATURE] main.py live test runner: calls every get.catalog and get.library function, logs to logs/ and saves JSON results to results/
+ [FEATURE] main.py helper that finds and calls every public member of an object
+ [TEST] Catalog tests extended to cover the playlist and stream endpoints
+ [ADD] readme field in pyproject.toml (PyPI long description)
+ [DOC] README: catalog.playlist(id) usage for public playlists
+ [BUILD] dist/ 0.8.3 and 0.9.0 wheel and tarball

~ [CHANGE] Token refresh failures raise typed exceptions (BadRequestError, AuthenticationError...) instead of a generic APIError
~ [REFACTOR] HTTP status → exception mapping centralised in error_from_response()
~ [FIX] exceptions.py compatible with Python 3.8+ (postponed annotations)
~ [DOC] README: error table, install command and known limitations updated
~ [FIX] README: parameter usage for playlist retrieval
~ [REFACTOR] main.py saves a specific playlist to temp.json
~ [CHORE] logs/ and results/ added to .gitignore
```

## Ver 0.8.3 - Sep 21, 2026

```diff
+ [FEATURE] catalog.playlist(id) implemented (no longer raises NotImplementedError)
+ [TEST] Playlist tests in TestCatalogPlaylist
+ [CI] GitHub Actions workflow to publish the Python package
```

## Ver 0.8.2 - Sep 12, 2026

```diff
+ [FEATURE] catalog.stream(id): track info and streaming URL
+ [DOC] README: stream method
+ [BUILD] dist/ 0.8.2 wheel and tarball

~ [FIX] HTTP success check accepts any 2xx status
~ [DOC] Installation instructions updated for 0.8.1
```

## Ver 0.8.1 - Sep 12, 2026

```diff
+ [BUILD] dist/ 0.8.1 wheel and tarball

~ [REFACTOR] Removed unnecessary comments and whitespace in client, catalog, library, progress, session and main
```

## Ver 0.8.0 - Sep 12, 2026

```diff
+ [FEATURE] Terminal spinner during network requests (only when stdout is a TTY)
+ [ADD] LICENSE file (MIT)
+ [DOC] README fully rewritten
+ [BUILD] dist/ 0.8.0 wheel and tarball

~ [REFACTOR] Code base split into modules: endpoints/catalog.py, endpoints/library.py, endpoints/verbs.py, progress.py, session.py
~ [FIX] Response handling accepts any 2xx status (was 200 only)
~ [FIX] main.py re-raises the exception after logging it
~ [DOC] License section in README

- [REMOVE] Unnecessary docstring on the _GET class
```

## Ver 0.7.6 - Sep 12, 2026

```diff
+ [FEATURE] Typed exceptions: AuthenticationError, NotFoundError, RateLimitError, ServerError (all inherit from APIError)
+ [FEATURE] Response parsing method in VoltaClient
+ [TEST] conftest.py fixtures updated for the new error handling
+ [BUILD] dist/ 0.7.6 tarball
```

## Ver 0.7.5 - Sep 12, 2026

```diff
+ [ADD] Error handling around main() execution
+ [DOC] Section header for API subspaces in VoltaClient
+ [BUILD] dist/ 0.7.4 and 0.7.5 wheel and tarball

~ [FIX] dist/ excluded from the built package
~ [FIX] Version accidentally bumped to 0.7.6, reverted to 0.7.5
~ [CHANGE] main.py fetches catalog state instead of a playlist
~ [CHORE] .coverage added to .gitignore

- [REMOVE] setup.py (packaging relies on pyproject.toml only)
- [REMOVE] Empty models.py
```

## Ver 0.7.4 - Sep 10, 2026

```diff
+ [BUILD] dist/ 0.7.3 tarball

~ [FIX] Homepage URL in pyproject.toml points to the new repository
```

## Ver 0.7.3 - Sep 10, 2026

```diff
+ [TEST] Tests for album, track, playlist, home, playback state and me endpoints

~ [FIX] catalog.playlist() raises NotImplementedError (upstream endpoint broken)
```

## Ver 0.7.2 - Sep 10, 2026

```diff
~ [FIX] state() docs reflect the current playback state endpoint
~ [CHANGE] main.py fetches the home catalog instead of a playlist
```

## Ver 0.7.1 - Sep 10, 2026

```diff
~ [FIX] playlist() returns False instead of None on failure
```

## Ver 0.7.0 - Sep 10, 2026

```diff
+ [FEATURE] Catalog methods: album, track, playlist, home, state, me
+ [DOC] GET.md: new endpoints and usage examples

~ [FIX] Playlist fetching in main()
```

## Ver 0.6.2 - Sep 9, 2026

```diff
~ [DOC] Renamed artists() to artist() in documentation
```

## Ver 0.6.1 - Sep 9, 2026

```diff
+ [FEATURE] catalog.artist(id): artist details, top tracks and albums
+ [TEST] Tests for artist catalog retrieval and URL construction
+ [CI] GitHub Actions workflow for the Python application
+ [ADD] requirements.txt (dotenv, requests)
+ [ADD] scripts.sh
+ [DOC] Changelog for 0.6.0
+ [DOC] GET.md: new structure, table of contents, artist details section

~ [REFACTOR] get_token.sh and update.sh moved to scripts/
~ [CHORE] .vscode/ added to .gitignore

- [REMOVE] Unused atexit import in client.py
```

## Ver 0.6.0 - Aug 30, 2026

```diff
+ [ADD] Homepage URL in pyproject.toml
+ [DOC] Section separators in GET.md

~ [REFACTOR] All tests in tests/ refactored
~ [FIX] Version renamed from "ALPHA 0.6.0" to "0.6.0"
```

## Ver 0.5.0 - Aug 30, 2026

```diff
+ [FEATURE] Global catalog search
+ [FEATURE] Update script reads the current version automatically
+ [DOC] GET.md: search, artist_albums, artist_tracks, playlists and global app sections

- [REMOVE] Unnecessary line breaks in GET.md
```

## Ver 0.4.0 - Aug 30, 2026

```diff
+ [FEATURE] search= parameter on library tracks, albums and artists
+ [FEATURE] playlists() accepts search= or id=
+ [TEST] Tests for GET, POST and DELETE methods
```

## Ver 0.3.5 - Aug 30, 2026

```diff
+ [FEATURE] PUT request

~ [CHORE] .pytest_cache added to .gitignore
```

## Ver 0.3.4 - Aug 30, 2026

```diff
+ [FEATURE] DELETE request with optional data parameter
+ [FEATURE] Update script for version management (pyproject.toml and setup.py)
+ [TEST] First test suite for VoltaClient

~ [FIX] Regex in the update script
```

## Ver 0.3.3 - Aug 30, 2026

```diff
~ [REFACTOR] Client and main module
```

## Ver 0.3.2 - Aug 30, 2026

```diff
+ [FEATURE] POST method for track creation
+ [DOC] docs/GET.md with library functions

~ [REFACTOR] Code structure and README
```

## Ver 0.3.1 - Aug 30, 2026

```diff
~ [REFACTOR] Simplified request method
~ [REFACTOR] token.json output formatted

- [REMOVE] Unused timing refresh function
```

## Ver 0.3.0 - Aug 30, 2026

```diff
+ [DOC] README with library usage examples

~ [REFACTOR] VoltaClient methods
```

## Ver 0.2.1 - Aug 30, 2026

```diff
+ [FEATURE] POST request
+ [DOC] README with usage instructions

~ [CHORE] main.py added to .gitignore
```

## Ver 0.2.0 - Aug 30, 2026

```diff
+ [FEATURE] GET request
```

## Ver 0.1.4 - Aug 29, 2026

```diff
+ [FEATURE] Token saved to disk and refreshed automatically
```

## Ver 0.1.3 - Aug 29, 2026

```diff
+ [FEATURE] Initial VoltaClient implementation
+ [ADD] Base exceptions
+ [ADD] get_token.sh script
+ [ADD] pyproject.toml and setup.py packaging
```

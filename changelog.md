# Changelog

All notable changes to VoltaLib, newest first. Each version lists every change made since the previous one.

Legend: `+` added · `~` changed / fixed · `-` removed

---

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

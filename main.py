import json
import logging
import os
import shutil
import time
from datetime import datetime

from VoltaLibPython import VoltaClient
from VoltaLibPython.exceptions import VoltaAPIExceptions

RESULTS_DIR = "results"
LOGS_DIR = "logs"

# IDs used by the tests. Leave one as None to auto-detect it from the search / library results.
SEARCH_QUERY = "daft punk"
TRACK_ID = "USUM72601820"
PLAYLIST_ID = "bb7d0e57-bb01-4491-88b6-ce62ee3d75f0"
ARTIST_ID = None
ALBUM_ID = None

logger = logging.getLogger("volta_tests")


def setup_logging():
    os.makedirs(LOGS_DIR, exist_ok=True)
    log_file = os.path.join(LOGS_DIR, f"test_{datetime.now():%Y-%m-%d_%H-%M-%S}.log")

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)
    root.addHandler(console_handler)
    return log_file


def find_id(data, key):
    """Return the "id" of the first dict found under `key` anywhere in `data`, or None."""
    if isinstance(data, dict):
        value = data.get(key)
        if isinstance(value, list) and value and isinstance(value[0], dict) and "id" in value[0]:
            return value[0]["id"]
        if isinstance(value, dict) and "id" in value:
            return value["id"]
        for child in data.values():
            found = find_id(child, key)
            if found:
                return found
    elif isinstance(data, list):
        if key is None and data and isinstance(data[0], dict):
            return data[0].get("id")
        for child in data:
            found = find_id(child, key)
            if found:
                return found
    return None


def run_test(group, name, func, *args, **kwargs):
    """Call one endpoint, log the outcome and save the result to results/<group>/<name>.json."""
    call = f"{group}.{name}({', '.join([repr(a) for a in args] + [f'{k}={v!r}' for k, v in kwargs.items()])})"
    logger.info(f"-> {call}")
    start = time.perf_counter()
    try:
        result = func(*args, **kwargs)
    except Exception as e:
        elapsed = time.perf_counter() - start
        logger.error(f"FAIL {call} after {elapsed:.2f}s: {type(e).__name__}: {e}")
        logger.debug("Traceback:", exc_info=True)
        payload = {"call": call, "ok": False, "error": type(e).__name__, "message": str(e)}
        ok = False
    else:
        elapsed = time.perf_counter() - start
        size = len(result) if isinstance(result, (list, dict)) else None
        logger.info(f"OK   {call} in {elapsed:.2f}s (type={type(result).__name__}, size={size})")
        payload = {"call": call, "ok": True, "elapsed_s": round(elapsed, 3), "result": result}
        ok = True

    os.makedirs(os.path.join(RESULTS_DIR, group), exist_ok=True)
    with open(os.path.join(RESULTS_DIR, group, f"{name}.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4, ensure_ascii=False, default=str)
    return ok, result if ok else None


def test_catalog(client):
    catalog = client.get.catalog
    results = {}

    ok, search = run_test("catalog", "search", catalog.search, SEARCH_QUERY)
    results["search"] = ok

    artist_id = ARTIST_ID or find_id(search, "artists")
    album_id = ALBUM_ID or find_id(search, "albums")

    for name, func, arg in [
        ("artist", catalog.artist, artist_id),
        ("album", catalog.album, album_id),
        ("track", catalog.track, TRACK_ID),
        ("playlist", catalog.playlist, PLAYLIST_ID),
        ("stream", catalog.stream, TRACK_ID),
    ]:
        if arg is None:
            logger.warning(f"SKIP catalog.{name}: no id available (set it at the top of main.py)")
            results[name] = None
            continue
        results[name], _ = run_test("catalog", name, func, arg)

    for name in ("home", "state", "me"):
        results[name], _ = run_test("catalog", name, getattr(catalog, name))

    return results


def test_library(client):
    library = client.get.library
    results = {}

    results["tracks"], _ = run_test("library", "tracks", library.tracks)
    results["tracks_search"], _ = run_test("library", "tracks_search", library.tracks, search=SEARCH_QUERY)
    results["albums"], _ = run_test("library", "albums", library.albums)
    results["albums_search"], _ = run_test("library", "albums_search", library.albums, search=SEARCH_QUERY)
    results["artists"], artists = run_test("library", "artists", library.artists)
    results["artists_search"], _ = run_test("library", "artists_search", library.artists, search=SEARCH_QUERY)
    results["playlists"], playlists = run_test("library", "playlists", library.playlists)
    results["playlists_search"], _ = run_test("library", "playlists_search", library.playlists, search=SEARCH_QUERY)

    artist_id = ARTIST_ID or find_id(artists, None) or find_id(artists, "artists")
    if artist_id:
        results["artist_albums"], _ = run_test("library", "artist_albums", library.artist_albums, artist_id)
        results["artist_tracks"], _ = run_test("library", "artist_tracks", library.artist_tracks, artist_id)
    else:
        logger.warning("SKIP library.artist_albums / artist_tracks: no artist id available")
        results["artist_albums"] = results["artist_tracks"] = None

    playlist_id = find_id(playlists, None) or find_id(playlists, "playlists")
    if playlist_id:
        results["playlist_by_id"], _ = run_test("library", "playlist_by_id", library.playlists, id=playlist_id)
    else:
        logger.warning("SKIP library.playlists(id=...): no playlist in your library")
        results["playlist_by_id"] = None

    return results


def run_all_tests():
    log_file = setup_logging()
    logger.info(f"Logs: {log_file} | Results: {RESULTS_DIR}/")

    with VoltaClient(show_progress=True) as client:
        summary = {"catalog": test_catalog(client), "library": test_library(client)}

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=4)

    for group, tests in summary.items():
        passed = sum(1 for v in tests.values() if v is True)
        failed = sum(1 for v in tests.values() if v is False)
        skipped = sum(1 for v in tests.values() if v is None)
        logger.info(f"{group}: {passed} OK, {failed} FAIL, {skipped} SKIP")


def main():
    run_all_tests()

def pause():
    input(f"Press Enter to exit and delete {RESULTS_DIR}/...")

def clear():
    """Delete only what this script produced (the results/ folder), never
    other .json files that happen to sit in the current directory."""
    shutil.rmtree(RESULTS_DIR, ignore_errors=True)


if __name__ == "__main__":
    try:
        main()
    except VoltaAPIExceptions as e:
        logger.debug("Traceback:", exc_info=True)
        print(f"\n[ERREUR] {type(e).__name__}: {e}\n")
    except Exception as e:
        print(f"An error occurred: {e}")
        raise
    pause()
    clear()

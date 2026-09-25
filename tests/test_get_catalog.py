"""
Tests pour client.get.catalog.

Lancer avec : pytest tests/test_get_catalog.py -v
"""

from __future__ import annotations

import pytest
import requests

from VoltaLibPython.exceptions import APIError

from .conftest import FakeResponse


class TestCatalogSearch:
    def test_search_success_returns_json(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(
            FakeResponse(200, {"tracks": [], "artists": [], "albums": [], "playlists": []})
        )

        result = client.get.catalog.search("daft punk")

        assert result == {"tracks": [], "artists": [], "albums": [], "playlists": []}

    def test_search_builds_expected_url(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(200, {}))

        client.get.catalog.search("daft punk")

        _, url, _, params = fake_session.calls[0]
        assert url.endswith("/api/v1/search")
        assert params == {"q": "daft punk"}

    def test_search_query_with_special_characters_is_encoded(self, make_client, fake_session):
        # Avant : "daft & punk" coupait la requête en deux paramètres.
        client = make_client()
        fake_session.get_responses.append(FakeResponse(200, {}))

        client.get.catalog.search("daft & punk #1")

        _, url, _, params = fake_session.calls[0]
        assert params == {"q": "daft & punk #1"}
        prepared = requests.Request("GET", url, params=params).prepare()
        assert prepared.url.endswith("/api/v1/search?q=daft+%26+punk+%231")

    def test_search_non_200_raises_api_error(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(500, text="internal error"))

        with pytest.raises(APIError):
            client.get.catalog.search("daft punk")

    def test_search_401_refreshes_token_and_retries_transparently(
        self, make_client, fake_session
    ):
        client = make_client({"access_token": "old_token", "expires_in": 3600})

        fake_session.get_responses.append(FakeResponse(401, text="invalid"))
        fake_session.post_responses.append(
            FakeResponse(200, {"access_token": "new_token", "expires_in": 3600})
        )
        fake_session.get_responses.append(FakeResponse(200, {"tracks": []}))

        result = client.get.catalog.search("daft punk")

        assert result == {"tracks": []}
        assert client.token == "new_token"


class TestCatalogArtist:
    def test_artist_success_returns_json(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(
            FakeResponse(200, {"id": "artist_1", "name": "Daft Punk", "top_tracks": [], "albums": []})
        )

        result = client.get.catalog.artist("artist_1")

        assert result == {"id": "artist_1", "name": "Daft Punk", "top_tracks": [], "albums": []}

    def test_artist_builds_expected_url(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(200, {}))

        client.get.catalog.artist("artist_1")

        method, url, headers, params = fake_session.calls[0]
        assert method == "GET"
        assert url.endswith("/api/v1/artists/artist_1")
        assert headers["Authorization"] == "Bearer initial_token"
        assert params is None

    def test_artist_uses_path_segment_not_query_param(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(200, {}))

        client.get.catalog.artist("artist_1")

        _, url, _, _ = fake_session.calls[0]
        assert "?" not in url

    def test_artist_non_200_raises_api_error(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(404, text="artist not found"))

        with pytest.raises(APIError):
            client.get.catalog.artist("unknown_id")

    def test_artist_401_refreshes_token_and_retries_transparently(
        self, make_client, fake_session
    ):
        client = make_client({"access_token": "old_token", "expires_in": 3600})

        fake_session.get_responses.append(FakeResponse(401, text="invalid"))
        fake_session.post_responses.append(
            FakeResponse(200, {"access_token": "new_token", "expires_in": 3600})
        )
        fake_session.get_responses.append(FakeResponse(200, {"id": "artist_1"}))

        result = client.get.catalog.artist("artist_1")

        assert result == {"id": "artist_1"}
        assert client.token == "new_token"

    def test_artist_401_twice_raises_after_single_retry(self, make_client, fake_session):
        client = make_client({"access_token": "old_token", "expires_in": 3600})

        fake_session.get_responses.append(FakeResponse(401, text="invalid"))
        fake_session.post_responses.append(
            FakeResponse(200, {"access_token": "new_token", "expires_in": 3600})
        )
        fake_session.get_responses.append(FakeResponse(401, text="invalid"))

        with pytest.raises(APIError):
            client.get.catalog.artist("artist_1")

        get_calls = [c for c in fake_session.calls if c[0] == "GET"]
        assert len(get_calls) == 2

    def test_artist_different_ids_build_different_urls(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(200, {"id": "a1"}))
        fake_session.get_responses.append(FakeResponse(200, {"id": "a2"}))

        client.get.catalog.artist("a1")
        client.get.catalog.artist("a2")

        urls = [c[1] for c in fake_session.calls]
        assert urls[0].endswith("/api/v1/artists/a1")
        assert urls[1].endswith("/api/v1/artists/a2")


class TestCatalogAlbum:
    def test_album_success_returns_json(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(
            FakeResponse(200, {"id": "al1", "title": "Discovery", "tracks": []})
        )

        result = client.get.catalog.album("al1")

        assert result == {"id": "al1", "title": "Discovery", "tracks": []}

    def test_album_builds_expected_url(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(200, {}))

        client.get.catalog.album("al1")

        method, url, headers, params = fake_session.calls[0]
        assert method == "GET"
        assert url.endswith("/api/v1/album/al1")
        assert headers["Authorization"] == "Bearer initial_token"
        assert params is None

    def test_album_non_200_raises_api_error(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(404, text="album not found"))

        with pytest.raises(APIError):
            client.get.catalog.album("unknown_id")

    def test_album_401_refreshes_token_and_retries_transparently(
        self, make_client, fake_session
    ):
        client = make_client({"access_token": "old_token", "expires_in": 3600})

        fake_session.get_responses.append(FakeResponse(401, text="invalid"))
        fake_session.post_responses.append(
            FakeResponse(200, {"access_token": "new_token", "expires_in": 3600})
        )
        fake_session.get_responses.append(FakeResponse(200, {"id": "al1"}))

        result = client.get.catalog.album("al1")

        assert result == {"id": "al1"}
        assert client.token == "new_token"


class TestCatalogTrack:
    def test_track_success_returns_json(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(
            FakeResponse(200, {"id": "t1", "title": "One More Time"})
        )

        result = client.get.catalog.track("t1")

        assert result == {"id": "t1", "title": "One More Time"}

    def test_track_builds_expected_url(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(200, {}))

        client.get.catalog.track("t1")

        method, url, headers, params = fake_session.calls[0]
        assert method == "GET"
        assert url.endswith("/api/v1/track/t1")
        assert params is None

    def test_track_non_200_raises_api_error(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(404, text="track not found"))

        with pytest.raises(APIError):
            client.get.catalog.track("unknown_id")

    def test_track_401_refreshes_token_and_retries_transparently(
        self, make_client, fake_session
    ):
        client = make_client({"access_token": "old_token", "expires_in": 3600})

        fake_session.get_responses.append(FakeResponse(401, text="invalid"))
        fake_session.post_responses.append(
            FakeResponse(200, {"access_token": "new_token", "expires_in": 3600})
        )
        fake_session.get_responses.append(FakeResponse(200, {"id": "t1"}))

        result = client.get.catalog.track("t1")

        assert result == {"id": "t1"}
        assert client.token == "new_token"


class TestCatalogPlaylist:
    """L'endpoint amont est de nouveau fonctionnel : ces tests suivent
    maintenant exactement le même schéma que TestCatalogAlbum/TestCatalogTrack
    (succès, URL, 401 avec retry, non-200 qui lève APIError) au lieu de
    verrouiller le comportement `NotImplementedError` précédent."""

    def test_playlist_success_returns_json(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(
            FakeResponse(200, {"id": "pl_123", "name": "Roadtrip 2024", "tracks": []})
        )

        result = client.get.catalog.playlist("pl_123")

        assert result == {"id": "pl_123", "name": "Roadtrip 2024", "tracks": []}

    def test_playlist_builds_expected_url(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(200, {}))

        client.get.catalog.playlist("pl_123")

        method, url, headers, params = fake_session.calls[0]
        assert method == "GET"
        assert url.endswith("/api/v1/playlist/pl_123")
        assert headers["Authorization"] == "Bearer initial_token"
        assert params is None

    def test_playlist_non_200_raises_api_error(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(404, text="playlist not found"))

        with pytest.raises(APIError):
            client.get.catalog.playlist("unknown_id")

    def test_playlist_401_refreshes_token_and_retries_transparently(
        self, make_client, fake_session
    ):
        client = make_client({"access_token": "old_token", "expires_in": 3600})

        fake_session.get_responses.append(FakeResponse(401, text="invalid"))
        fake_session.post_responses.append(
            FakeResponse(200, {"access_token": "new_token", "expires_in": 3600})
        )
        fake_session.get_responses.append(FakeResponse(200, {"id": "pl_123"}))

        result = client.get.catalog.playlist("pl_123")

        assert result == {"id": "pl_123"}
        assert client.token == "new_token"

    def test_playlist_401_twice_raises_after_single_retry(self, make_client, fake_session):
        client = make_client({"access_token": "old_token", "expires_in": 3600})

        fake_session.get_responses.append(FakeResponse(401, text="invalid"))
        fake_session.post_responses.append(
            FakeResponse(200, {"access_token": "new_token", "expires_in": 3600})
        )
        fake_session.get_responses.append(FakeResponse(401, text="invalid"))

        with pytest.raises(APIError):
            client.get.catalog.playlist("pl_123")

        get_calls = [c for c in fake_session.calls if c[0] == "GET"]
        assert len(get_calls) == 2


class TestCatalogStream:
    def test_stream_success_returns_json(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(
            FakeResponse(
                200,
                {
                    "track_id": "t1",
                    "stream_url": "/api/v1/stream_relay_ref?ref=volta_relay_ref_xxx",
                },
            )
        )

        result = client.get.catalog.stream("t1")

        assert result == {
            "track_id": "t1",
            "stream_url": "/api/v1/stream_relay_ref?ref=volta_relay_ref_xxx",
        }

    def test_stream_builds_expected_url(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(200, {}))

        client.get.catalog.stream("t1")

        method, url, headers, params = fake_session.calls[0]
        assert method == "GET"
        assert url.endswith("/api/v1/stream")
        assert headers["Authorization"] == "Bearer initial_token"
        assert params == {"track_id": "t1"}

    def test_stream_non_200_raises_api_error(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(404, text="track not found"))

        with pytest.raises(APIError):
            client.get.catalog.stream("unknown_id")

    def test_stream_401_refreshes_token_and_retries_transparently(
        self, make_client, fake_session
    ):
        client = make_client({"access_token": "old_token", "expires_in": 3600})

        fake_session.get_responses.append(FakeResponse(401, text="invalid"))
        fake_session.post_responses.append(
            FakeResponse(200, {"access_token": "new_token", "expires_in": 3600})
        )
        fake_session.get_responses.append(FakeResponse(200, {"track_id": "t1"}))

        result = client.get.catalog.stream("t1")

        assert result == {"track_id": "t1"}
        assert client.token == "new_token"

    def test_stream_different_ids_build_different_urls(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(200, {"track_id": "t1"}))
        fake_session.get_responses.append(FakeResponse(200, {"track_id": "t2"}))

        client.get.catalog.stream("t1")
        client.get.catalog.stream("t2")

        params = [c[3] for c in fake_session.calls]
        assert params == [{"track_id": "t1"}, {"track_id": "t2"}]


class TestCatalogHome:
    def test_home_success_returns_json(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(
            FakeResponse(200, {"sections": [{"title": "Nouveautés", "items": []}]})
        )

        result = client.get.catalog.home()

        assert result == {"sections": [{"title": "Nouveautés", "items": []}]}

    def test_home_builds_expected_url(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(200, {}))

        client.get.catalog.home()

        method, url, headers, params = fake_session.calls[0]
        assert method == "GET"
        assert url.endswith("/api/v1/home")
        assert params is None

    def test_home_non_200_raises_api_error(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(500, text="internal error"))

        with pytest.raises(APIError):
            client.get.catalog.home()

    def test_home_401_refreshes_token_and_retries_transparently(
        self, make_client, fake_session
    ):
        client = make_client({"access_token": "old_token", "expires_in": 3600})

        fake_session.get_responses.append(FakeResponse(401, text="invalid"))
        fake_session.post_responses.append(
            FakeResponse(200, {"access_token": "new_token", "expires_in": 3600})
        )
        fake_session.get_responses.append(FakeResponse(200, {"sections": []}))

        result = client.get.catalog.home()

        assert result == {"sections": []}
        assert client.token == "new_token"


class TestCatalogPlaybackState:
    def test_state_success_returns_json(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(
            FakeResponse(200, {"is_playing": True, "track_id": "t1"})
        )

        result = client.get.catalog.state()

        assert result == {"is_playing": True, "track_id": "t1"}

    def test_state_builds_expected_url(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(200, {}))

        client.get.catalog.state()

        method, url, headers, params = fake_session.calls[0]
        assert method == "GET"
        assert url.endswith("/api/v1/playback/state")
        assert params is None

    def test_state_non_200_raises_api_error(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(500, text="internal error"))

        with pytest.raises(APIError):
            client.get.catalog.state()

    def test_state_401_refreshes_token_and_retries_transparently(
        self, make_client, fake_session
    ):
        client = make_client({"access_token": "old_token", "expires_in": 3600})

        fake_session.get_responses.append(FakeResponse(401, text="invalid"))
        fake_session.post_responses.append(
            FakeResponse(200, {"access_token": "new_token", "expires_in": 3600})
        )
        fake_session.get_responses.append(FakeResponse(200, {"is_playing": False}))

        result = client.get.catalog.state()

        assert result == {"is_playing": False}
        assert client.token == "new_token"


class TestCatalogMe:
    def test_me_success_returns_json(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(
            FakeResponse(200, {"sub": "u1", "preferred_username": "hugoh", "picture": "https://cdn.test/a.jpg"})
        )

        result = client.get.catalog.me()

        assert result == {"sub": "u1", "preferred_username": "hugoh", "picture": "https://cdn.test/a.jpg"}

    def test_me_builds_expected_url(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(200, {}))

        client.get.catalog.me()

        method, url, headers, params = fake_session.calls[0]
        assert method == "GET"
        assert url.endswith("/api/v1/auth/me")
        assert headers["Authorization"] == "Bearer initial_token"
        assert params is None

    def test_me_non_200_raises_api_error(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(403, text="forbidden"))

        with pytest.raises(APIError):
            client.get.catalog.me()

    def test_me_401_refreshes_token_and_retries_transparently(
        self, make_client, fake_session
    ):
        client = make_client({"access_token": "old_token", "expires_in": 3600})

        fake_session.get_responses.append(FakeResponse(401, text="invalid"))
        fake_session.post_responses.append(
            FakeResponse(200, {"access_token": "new_token", "expires_in": 3600})
        )
        fake_session.get_responses.append(FakeResponse(200, {"username": "hugoh"}))

        result = client.get.catalog.me()

        assert result == {"username": "hugoh"}
        assert client.token == "new_token"

class TestPathEncoding:
    @pytest.mark.parametrize(
        "call, expected",
        [
            (lambda c: c.get.catalog.artist("a/b"), "/api/v1/artists/a%2Fb"),
            (lambda c: c.get.catalog.album("x?y=1"), "/api/v1/album/x%3Fy%3D1"),
            (lambda c: c.get.catalog.track("t#1"), "/api/v1/track/t%231"),
            (lambda c: c.get.catalog.playlist("my list"), "/api/v1/playlist/my%20list"),
            (lambda c: c.get.library.artist_albums("../admin"), "/api/v1/library/artists/..%2Fadmin/albums"),
            (lambda c: c.get.library.playlists(id="p/1"), "/api/v1/library/playlists/p%2F1"),
        ],
    )
    def test_ids_cannot_change_the_route(self, make_client, fake_session, call, expected):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(200, {}))

        call(client)

        _, url, _, _ = fake_session.calls[0]
        assert url.endswith(expected)

    def test_plain_ids_are_unchanged(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(200, {}))

        client.get.catalog.playlist("bb7d0e57-bb01-4491-88b6-ce62ee3d75f0")

        _, url, _, _ = fake_session.calls[0]
        assert url.endswith("/api/v1/playlist/bb7d0e57-bb01-4491-88b6-ce62ee3d75f0")


class TestGenericGetRequest:
    def test_get_request_calls_the_given_endpoint(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(200, {"ok": True}))

        result = client.get.request("/api/v1/custom")

        assert result == {"ok": True}
        method, url, _, params = fake_session.calls[0]
        assert (method, url, params) == ("GET", "https://api.volta-music.test/api/v1/custom", None)

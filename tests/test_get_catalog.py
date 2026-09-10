"""
Tests pour client.get.catalog.

Lancer avec : pytest tests/test_get_catalog.py -v
"""

from __future__ import annotations

import pytest

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
        assert url.endswith("/api/v1/search?q=daft punk")
        # Le paramètre q est concaténé directement dans l'endpoint plutôt que
        # passé via `params=`, donc aucun `params` n'est transmis à la session.
        assert params is None

    def test_search_query_is_not_url_encoded(self, make_client, fake_session):
        """Comportement actuel documenté : `query` est inséré tel quel dans
        l'URL (`f"{endpoint}/search?q={query}"`) sans passer par
        `urllib.parse.quote` ni par le paramètre `params=` de requests, qui
        s'en chargerait automatiquement. Une requête contenant des espaces ou
        des caractères spéciaux (`&`, `#`, `=`, accents...) part donc non
        encodée. Ça fonctionne pour un mot simple mais peut casser l'appel
        réel à l'API pour des requêtes plus complexes — à corriger en passant
        par `params={"q": query}` si besoin."""
        client = make_client()
        fake_session.get_responses.append(FakeResponse(200, {}))

        client.get.catalog.search("daft & punk")

        _, url, _, _ = fake_session.calls[0]
        assert url.endswith("/api/v1/search?q=daft & punk")  # espace/& non encodés

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
            FakeResponse(
                200,
                {
                    "id": "artist_1",
                    "name": "Daft Punk",
                    "top_tracks": [],
                    "albums": [],
                },
            )
        )

        result = client.get.catalog.artist("artist_1")

        assert result == {
            "id": "artist_1",
            "name": "Daft Punk",
            "top_tracks": [],
            "albums": [],
        }

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
        # Contrairement à search(), l'id est un segment de chemin — pas de
        # "?" dans l'URL générée.
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
    """La vraie requête est actuellement commentée dans client.py :
    `playlist()` renvoie toujours `False` sans jamais appeler l'API. Ces
    tests verrouillent ce comportement actuel — ils échoueront (à raison)
    le jour où l'appel réel sera réactivé, ce qui te rappellera de les
    mettre à jour à ce moment-là (retirer ce test et écrire les mêmes
    scénarios que TestCatalogAlbum/TestCatalogTrack : succès, 401 avec
    retry, non-200 qui lève APIError)."""

    def test_playlist_currently_always_returns_false(self, make_client, fake_session):
        client = make_client()

        result = client.get.catalog.playlist("pl_123")

        assert result is False

    def test_playlist_currently_never_calls_the_api(self, make_client, fake_session):
        client = make_client()

        client.get.catalog.playlist("pl_123")

        assert fake_session.calls == []


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
            FakeResponse(200, {"username": "hugoh", "email": "hugo@example.com"})
        )

        result = client.get.catalog.me()

        assert result == {"username": "hugoh", "email": "hugo@example.com"}

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
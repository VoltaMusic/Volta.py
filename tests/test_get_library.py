"""
Tests pour client.get.library.

Lancer avec : pytest tests/test_get_library.py -v
"""

from __future__ import annotations

import pytest

from VoltaLibPython.exceptions import APIError, InvalidResponseError

from .conftest import FakeResponse


# ---------------------------------------------------------------------------
# tracks()
# ---------------------------------------------------------------------------

class TestLibraryTracks:
    def test_tracks_without_search_returns_raw_result(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(
            FakeResponse(200, [{"id": "t1", "title": "Random Access Memories"}])
        )

        result = client.get.library.tracks()

        assert result == [{"id": "t1", "title": "Random Access Memories"}]
        _, url, _, _ = fake_session.calls[0]
        assert url.endswith("/api/v1/library/tracks")

    def test_tracks_search_filters_by_title_case_insensitive(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(
            FakeResponse(
                200,
                [
                    {"id": "t1", "title": "Random Access Memories"},
                    {"id": "t2", "title": "Discovery"},
                    {"id": "t3", "title": "random thoughts"},
                ],
            )
        )

        result = client.get.library.tracks(search="RANDOM")

        assert [t["id"] for t in result] == ["t1", "t3"]

    def test_tracks_search_with_no_match_returns_empty_list(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(
            FakeResponse(200, [{"id": "t1", "title": "Discovery"}])
        )

        result = client.get.library.tracks(search="nope")

        assert result == []

    def test_tracks_search_ignores_items_without_dict_shape(self, make_client, fake_session):
        client = make_client()
        # Un élément qui n'est pas un dict (ex: donnée malformée côté API) ne
        # doit pas faire planter le filtrage, juste être ignoré.
        fake_session.get_responses.append(
            FakeResponse(200, [{"id": "t1", "title": "Discovery"}, "not_a_dict", None])
        )

        result = client.get.library.tracks(search="disco")

        assert result == [{"id": "t1", "title": "Discovery"}]

    def test_tracks_search_on_non_list_result_raises(self, make_client, fake_session):
        """Si l'API renvoie autre chose qu'une liste alors qu'un `search` est
        demandé, la méthode lève InvalidResponseError au lieu de renvoyer
        une liste vide qui ferait croire à tort qu'il n'y a aucun résultat."""
        client = make_client()
        fake_session.get_responses.append(FakeResponse(200, {"unexpected": "shape"}))

        with pytest.raises(InvalidResponseError, match="dict") as exc:
            client.get.library.tracks(search="disco")

        assert "unexpected" in str(exc.value)

    @pytest.mark.parametrize("method", ["tracks", "albums", "artists", "playlists"])
    def test_non_list_without_search_is_returned_as_is(self, make_client, fake_session, method):
        # Sans `search`, rien n'est filtré : la réponse brute est renvoyée.
        client = make_client()
        fake_session.get_responses.append(FakeResponse(200, {"unexpected": "shape"}))

        assert getattr(client.get.library, method)() == {"unexpected": "shape"}


# ---------------------------------------------------------------------------
# albums()
# ---------------------------------------------------------------------------

class TestLibraryAlbums:
    def test_albums_without_search_returns_raw_result(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(200, [{"id": "al1", "title": "Discovery"}]))

        result = client.get.library.albums()

        assert result == [{"id": "al1", "title": "Discovery"}]
        _, url, _, _ = fake_session.calls[0]
        assert url.endswith("/api/v1/library/albums")

    def test_albums_search_filters_by_title(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(
            FakeResponse(
                200,
                [
                    {"id": "al1", "title": "Discovery"},
                    {"id": "al2", "title": "Homework"},
                ],
            )
        )

        result = client.get.library.albums(search="disco")

        assert [a["id"] for a in result] == ["al1"]

    def test_albums_search_no_match_returns_empty_list(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(200, [{"id": "al1", "title": "Homework"}]))

        result = client.get.library.albums(search="zzz")

        assert result == []


# ---------------------------------------------------------------------------
# artists()
# ---------------------------------------------------------------------------

class TestLibraryArtists:
    def test_artists_without_search_returns_raw_result(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(200, [{"id": "a1", "name": "Daft Punk"}]))

        result = client.get.library.artists()

        assert result == [{"id": "a1", "name": "Daft Punk"}]
        _, url, _, _ = fake_session.calls[0]
        assert url.endswith("/api/v1/library/artists")

    def test_artists_search_filters_by_name_not_title(self, make_client, fake_session):
        """Contrairement à tracks()/albums() qui filtrent sur `title`,
        artists() filtre sur la clé `name` — test dédié pour verrouiller
        cette différence."""
        client = make_client()
        fake_session.get_responses.append(
            FakeResponse(
                200,
                [
                    {"id": "a1", "name": "Daft Punk"},
                    {"id": "a2", "name": "Justice"},
                ],
            )
        )

        result = client.get.library.artists(search="daft")

        assert [a["id"] for a in result] == ["a1"]

    def test_artists_search_ignores_title_key(self, make_client, fake_session):
        # Un item avec un `title` correspondant mais pas de `name` ne doit
        # jamais matcher pour artists() (clé de filtrage = "name").
        client = make_client()
        fake_session.get_responses.append(
            FakeResponse(200, [{"id": "a1", "title": "daft punk", "name": "Justice"}])
        )

        result = client.get.library.artists(search="daft")

        assert result == []


# ---------------------------------------------------------------------------
# artist_albums() / artist_tracks()
# ---------------------------------------------------------------------------

class TestLibraryArtistSubresources:
    def test_artist_albums_hits_expected_url(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(200, []))

        client.get.library.artist_albums("artist_1")

        _, url, _, _ = fake_session.calls[0]
        assert url.endswith("/api/v1/library/artists/artist_1/albums")

    def test_artist_tracks_hits_expected_url(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(200, []))

        client.get.library.artist_tracks("artist_1")

        _, url, _, _ = fake_session.calls[0]
        assert url.endswith("/api/v1/library/artists/artist_1/tracks")

    def test_artist_albums_401_refreshes_and_retries(self, make_client, fake_session):
        client = make_client({"access_token": "old_token", "expires_in": 3600})

        fake_session.get_responses.append(FakeResponse(401, text="invalid"))
        fake_session.post_responses.append(
            FakeResponse(200, {"access_token": "new_token", "expires_in": 3600})
        )
        fake_session.get_responses.append(FakeResponse(200, [{"id": "al1"}]))

        result = client.get.library.artist_albums("artist_1")

        assert result == [{"id": "al1"}]
        assert client.token == "new_token"


# ---------------------------------------------------------------------------
# playlists()
# ---------------------------------------------------------------------------

class TestLibraryPlaylists:
    def test_playlists_no_args_lists_all(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(200, [{"id": "pl1", "name": "Roadtrip"}]))

        result = client.get.library.playlists()

        assert result == [{"id": "pl1", "name": "Roadtrip"}]
        _, url, _, _ = fake_session.calls[0]
        assert url.endswith("/api/v1/library/playlists")

    def test_playlists_with_id_gets_single_playlist(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(200, {"id": "pl_123", "name": "Roadtrip"}))

        result = client.get.library.playlists(id="pl_123")

        assert result == {"id": "pl_123", "name": "Roadtrip"}
        _, url, _, _ = fake_session.calls[0]
        assert url.endswith("/api/v1/library/playlists/pl_123")

    def test_playlists_search_filters_by_name(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(
            FakeResponse(
                200,
                [
                    {"id": "pl1", "name": "Roadtrip 2024"},
                    {"id": "pl2", "name": "Chill"},
                ],
            )
        )

        result = client.get.library.playlists(search="roadtrip")

        assert [p["id"] for p in result] == ["pl1"]

    def test_playlists_search_no_match_returns_empty_list(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(200, [{"id": "pl1", "name": "Chill"}]))

        result = client.get.library.playlists(search="zzz")

        assert result == []

    def test_playlists_search_and_id_together_raises_value_error(self, make_client, fake_session):
        client = make_client()

        with pytest.raises(ValueError):
            client.get.library.playlists(search="roadtrip", id="pl_123")

        # La requête ne doit même pas partir : le garde-fou est avant l'appel réseau.
        assert fake_session.calls == []

    def test_playlists_id_takes_priority_when_search_is_none(self, make_client, fake_session):
        # id seul (search=None explicite) est un cas valide, pas une erreur.
        client = make_client()
        fake_session.get_responses.append(FakeResponse(200, {"id": "pl_123"}))

        result = client.get.library.playlists(search=None, id="pl_123")

        assert result == {"id": "pl_123"}

# ---------------------------------------------------------------------------
# Filtrage `search=` commun
# ---------------------------------------------------------------------------

class TestSearchFilter:
    @pytest.mark.parametrize(
        "method, key",
        [("tracks", "title"), ("albums", "title"), ("artists", "name"), ("playlists", "name")],
    )
    def test_search_is_accent_insensitive(self, make_client, fake_session, method, key):
        client = make_client()
        fake_session.get_responses.append(
            FakeResponse(200, [{"id": "1", key: "Beyoncé"}, {"id": "2", key: "Björk"}])
        )

        result = getattr(client.get.library, method)(search="beyonce")

        assert [item["id"] for item in result] == ["1"]

    def test_accented_query_matches_unaccented_title(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(200, [{"id": "t1", "title": "Cafe del Mar"}]))

        result = client.get.library.tracks(search="Café")

        assert [t["id"] for t in result] == ["t1"]

    def test_null_or_missing_field_is_ignored(self, make_client, fake_session):
        # Avant : un titre `null` faisait planter la recherche (None.lower()).
        client = make_client()
        fake_session.get_responses.append(
            FakeResponse(200, [{"id": "t1", "title": None}, {"id": "t2"}, {"id": "t3", "title": "Discovery"}])
        )

        result = client.get.library.tracks(search="disco")

        assert [t["id"] for t in result] == ["t3"]

    def test_casefold_handles_special_cases(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(200, [{"id": "a1", "name": "STRASSE"}]))

        result = client.get.library.artists(search="straße")

        assert [a["id"] for a in result] == ["a1"]

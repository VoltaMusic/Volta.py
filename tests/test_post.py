"""
Tests pour client.post.

Lancer avec : pytest tests/test_post.py -v
"""

from __future__ import annotations

import pytest

from VoltaLibPython.exceptions import APIError, ForbiddenError, InvalidArgumentError

from .conftest import FakeResponse

# Formes réelles renvoyées par l'API.
LIBRARY_TRACK = {  # get.library.tracks()
    "id": "89629777",
    "title": "Move Your Body",
    "artist": "Eiffel 65",
    "artist_id": "59",
    "album": "Move Your Body",
    "album_id": "vc_-9076737",
    "cover_url": "https://cdn.test/cover.jpg",
    "duration_ms": 268000,
    "added_at": "2026-09-12T10:43:37.981851",
    "in_library": True,
}
CATALOG_TRACK = {  # get.catalog.track() / search()
    "id": "ITT019910202",
    "name": "Move Your Body",
    "duration_ms": 268863,
    "artists": [{"id": "Gabry Ponte", "name": "Gabry Ponte"}, {"id": None, "name": "Eiffel 65"}],
    "album": {"id": "vc_1694", "name": "Europop", "images": [{"url": "https://cdn.test/a.jpg"}]},
    "popularity": 50,
}
LIBRARY_PAYLOAD = {
    "id": "89629777",
    "name": "Move Your Body",
    "artist": "Eiffel 65",
    "album": "Move Your Body",
    "artist_id": "59",
    "album_id": "vc_-9076737",
    "cover_url": "https://cdn.test/cover.jpg",
    "duration_ms": 268000,
}


class TestPost:
    def test_post_track_success(self, make_client, fake_session):
        client = make_client()
        fake_session.post_responses.append(FakeResponse(200, {"message": "Track added"}))

        result = client.post.library.track(LIBRARY_TRACK)

        assert result == {"message": "Track added"}
        method, url, headers, payload = fake_session.calls[0]
        assert method == "POST"
        assert url.endswith("/api/v1/library/tracks")
        assert payload == LIBRARY_PAYLOAD
        assert headers["Authorization"] == "Bearer initial_token"

    def test_post_401_refreshes_and_retries(self, make_client, fake_session):
        client = make_client({"access_token": "old_token", "expires_in": 3600})

        fake_session.post_responses.append(FakeResponse(401, text="invalid"))
        fake_session.post_responses.append(
            FakeResponse(200, {"access_token": "new_token", "expires_in": 3600})
        )
        fake_session.post_responses.append(FakeResponse(200, {"message": "ok"}))

        result = client.post.library.track(LIBRARY_TRACK)

        assert result == {"message": "ok"}
        assert client.token == "new_token"

    def test_post_401_twice_raises_after_single_retry(self, make_client, fake_session):
        client = make_client({"access_token": "old_token", "expires_in": 3600})

        fake_session.post_responses.append(FakeResponse(401, text="invalid"))
        fake_session.post_responses.append(
            FakeResponse(200, {"access_token": "new_token", "expires_in": 3600})
        )
        fake_session.post_responses.append(FakeResponse(401, text="invalid"))

        with pytest.raises(APIError):
            client.post.library.track(LIBRARY_TRACK)

        post_calls = [c for c in fake_session.calls if c[0] == "POST" and c[1].endswith("/tracks")]
        assert len(post_calls) == 2

    def test_post_non_200_raises_api_error(self, make_client, fake_session):
        client = make_client()
        fake_session.post_responses.append(FakeResponse(400, text="bad request"))

        with pytest.raises(APIError):
            client.post.library.track(LIBRARY_TRACK)

    def test_post_request_generic_endpoint(self, make_client, fake_session):
        client = make_client()
        fake_session.post_responses.append(FakeResponse(200, {"ok": True}))

        result = client.post.request("/api/v1/library/playlists", {"name": "Roadtrip"})

        assert result == {"ok": True}
        _, url, _, payload = fake_session.calls[0]
        assert url.endswith("/api/v1/library/playlists")
        assert payload == {"name": "Roadtrip"}


class TestTrackPayload:
    def test_catalog_track_is_converted(self, make_client, fake_session):
        client = make_client()
        fake_session.post_responses.append(FakeResponse(200, {}))

        client.post.library.track(CATALOG_TRACK)

        _, _, _, payload = fake_session.calls[0]
        assert payload == {
            "id": "ITT019910202",
            "name": "Move Your Body",
            "artist": "Gabry Ponte, Eiffel 65",
            "album": "Europop",
            "artist_id": "Gabry Ponte",
            "album_id": "vc_1694",
            "cover_url": "https://cdn.test/a.jpg",
            "duration_ms": 268863,
        }

    def test_unknown_fields_are_not_sent(self, make_client, fake_session):
        client = make_client()
        fake_session.post_responses.append(FakeResponse(200, {}))

        client.post.library.track(LIBRARY_TRACK)

        _, _, _, payload = fake_session.calls[0]
        assert "added_at" not in payload and "in_library" not in payload

    def test_minimal_track(self, make_client, fake_session):
        client = make_client()
        fake_session.post_responses.append(FakeResponse(200, {}))

        client.post.library.track({"id": 42, "name": "X", "artist": "Y", "album": "Z"})

        _, _, _, payload = fake_session.calls[0]
        assert payload == {"id": "42", "name": "X", "artist": "Y", "album": "Z"}

    def test_id_alone_raises_with_explanation(self, make_client, fake_session):
        client = make_client()

        with pytest.raises(InvalidArgumentError, match="whole track"):
            client.post.library.track("89629777")

        assert fake_session.calls == []

    def test_incomplete_track_lists_missing_fields(self, make_client, fake_session):
        client = make_client()

        with pytest.raises(InvalidArgumentError, match="artist, album"):
            client.post.library.playlist_track("pl1", {"id": "t1", "title": "X"})

        assert fake_session.calls == []

    def test_non_dict_raises(self, make_client, fake_session):
        client = make_client()

        with pytest.raises(InvalidArgumentError, match="list"):
            client.post.library.track(["t1"])


class TestPostLibrary:
    def test_playlist_sends_only_given_fields(self, make_client, fake_session):
        client = make_client()
        fake_session.post_responses.append(FakeResponse(200, {"id": "pl1"}))

        result = client.post.library.playlist("Roadtrip")

        assert result == {"id": "pl1"}
        _, url, _, payload = fake_session.calls[0]
        assert url.endswith("/api/v1/library/playlists")
        assert payload == {"name": "Roadtrip"}
        assert len(fake_session.calls) == 1

    def test_playlist_with_all_fields(self, make_client, fake_session):
        client = make_client()
        fake_session.post_responses.append(FakeResponse(200, {"id": "pl1", "description": "Summer"}))

        client.post.library.playlist("Roadtrip", description="Summer", is_public=False)

        _, _, _, payload = fake_session.calls[0]
        # is_public=False doit être envoyé : seul None veut dire "absent".
        assert payload == {"name": "Roadtrip", "description": "Summer", "is_public": False}

    def test_description_ignored_on_creation_is_set_with_put(self, make_client, fake_session):
        # Comportement réel de l'API : la description revient à null à la création.
        client = make_client()
        fake_session.post_responses.append(FakeResponse(200, {"id": "pl1", "name": "Roadtrip", "description": None}))
        fake_session.put_responses.append(FakeResponse(200, {"id": "pl1", "description": "Summer"}))

        result = client.post.library.playlist("Roadtrip", description="Summer")

        method, url, _, payload = fake_session.calls[1]
        assert method == "PUT"
        assert url.endswith("/api/v1/library/playlists/pl1")
        assert payload == {"description": "Summer"}
        assert result == {"id": "pl1", "name": "Roadtrip", "description": "Summer"}

    def test_description_kept_on_creation_needs_no_put(self, make_client, fake_session):
        client = make_client()
        fake_session.post_responses.append(FakeResponse(200, {"id": "pl1", "description": "Summer"}))

        client.post.library.playlist("Roadtrip", description="Summer")

        assert [c[0] for c in fake_session.calls] == ["POST"]

    def test_playlist_without_name_raises_before_request(self, make_client, fake_session):
        client = make_client()

        with pytest.raises(ValueError):
            client.post.library.playlist("")

        assert fake_session.calls == []

    def test_playlist_track_hits_expected_url(self, make_client, fake_session):
        client = make_client()
        fake_session.post_responses.append(FakeResponse(200, {"message": "Track added to playlist"}))

        client.post.library.playlist_track("pl1", LIBRARY_TRACK)

        _, url, _, payload = fake_session.calls[0]
        assert url.endswith("/api/v1/library/playlists/pl1/tracks")
        assert payload == LIBRARY_PAYLOAD

    def test_403_missing_scope_raises_forbidden(self, make_client, fake_session):
        client = make_client()
        fake_session.post_responses.append(FakeResponse(403, {"detail": "missing scope playlists:write"}))

        with pytest.raises(ForbiddenError):
            client.post.library.playlist("Roadtrip")


class TestPlaylistDescriptionFallback:
    def test_non_dict_put_response_keeps_created_playlist(self, make_client, fake_session):
        client = make_client()
        fake_session.post_responses.append(FakeResponse(200, {"id": "pl1", "name": "Roadtrip", "description": None}))
        fake_session.put_responses.append(FakeResponse(200, []))

        result = client.post.library.playlist("Roadtrip", description="Summer")

        assert result == {"id": "pl1", "name": "Roadtrip", "description": None}

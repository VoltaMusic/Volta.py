"""
Tests pour client.post.

Lancer avec : pytest tests/test_post.py -v
"""

from __future__ import annotations

import pytest

from VoltaLibPython.exceptions import APIError, ForbiddenError

from .conftest import FakeResponse


class TestPost:
    def test_post_track_success(self, make_client, fake_session):
        client = make_client()
        fake_session.post_responses.append(FakeResponse(200, {"id": "t1"}))

        result = client.post.library.track("t1")

        assert result == {"id": "t1"}
        method, url, headers, payload = fake_session.calls[0]
        assert method == "POST"
        assert url.endswith("/api/v1/library/tracks")
        assert payload == {"track_id": "t1"}
        assert headers["Authorization"] == "Bearer initial_token"

    def test_post_401_refreshes_and_retries(self, make_client, fake_session):
        client = make_client({"access_token": "old_token", "expires_in": 3600})

        fake_session.post_responses.append(FakeResponse(401, text="invalid"))
        fake_session.post_responses.append(
            FakeResponse(200, {"access_token": "new_token", "expires_in": 3600})
        )
        fake_session.post_responses.append(FakeResponse(200, {"id": "t1"}))

        result = client.post.library.track("t1")

        assert result == {"id": "t1"}
        assert client.token == "new_token"

    def test_post_401_twice_raises_after_single_retry(self, make_client, fake_session):
        client = make_client({"access_token": "old_token", "expires_in": 3600})

        fake_session.post_responses.append(FakeResponse(401, text="invalid"))
        fake_session.post_responses.append(
            FakeResponse(200, {"access_token": "new_token", "expires_in": 3600})
        )
        fake_session.post_responses.append(FakeResponse(401, text="invalid"))

        with pytest.raises(APIError):
            client.post.library.track("t1")

        post_calls = [c for c in fake_session.calls if c[0] == "POST" and c[1].endswith("/tracks")]
        assert len(post_calls) == 2

    def test_post_non_200_raises_api_error(self, make_client, fake_session):
        client = make_client()
        fake_session.post_responses.append(FakeResponse(400, text="bad request"))

        with pytest.raises(APIError):
            client.post.library.track("t1")

    def test_post_request_generic_endpoint(self, make_client, fake_session):
        client = make_client()
        fake_session.post_responses.append(FakeResponse(200, {"ok": True}))

        result = client.post.request("/api/v1/library/playlists", {"name": "Roadtrip"})

        assert result == {"ok": True}
        _, url, _, payload = fake_session.calls[0]
        assert url.endswith("/api/v1/library/playlists")
        assert payload == {"name": "Roadtrip"}

class TestPostLibrary:
    def test_track_sends_track_id(self, make_client, fake_session):
        client = make_client()
        fake_session.post_responses.append(FakeResponse(200, {"ok": True}))

        client.post.library.track("t1")

        method, url, _, payload = fake_session.calls[0]
        assert method == "POST"
        assert url.endswith("/api/v1/library/tracks")
        assert payload == {"track_id": "t1"}

    def test_playlist_sends_only_given_fields(self, make_client, fake_session):
        client = make_client()
        fake_session.post_responses.append(FakeResponse(200, {"id": "pl1"}))

        result = client.post.library.playlist("Roadtrip")

        assert result == {"id": "pl1"}
        _, url, _, payload = fake_session.calls[0]
        assert url.endswith("/api/v1/library/playlists")
        assert payload == {"name": "Roadtrip"}

    def test_playlist_with_all_fields(self, make_client, fake_session):
        client = make_client()
        fake_session.post_responses.append(FakeResponse(200, {"id": "pl1"}))

        client.post.library.playlist("Roadtrip", description="Summer", is_public=False)

        _, _, _, payload = fake_session.calls[0]
        # is_public=False doit être envoyé : seul None veut dire "absent".
        assert payload == {"name": "Roadtrip", "description": "Summer", "is_public": False}

    def test_playlist_without_name_raises_before_request(self, make_client, fake_session):
        client = make_client()

        with pytest.raises(ValueError):
            client.post.library.playlist("")

        assert fake_session.calls == []

    def test_playlist_track_hits_expected_url(self, make_client, fake_session):
        client = make_client()
        fake_session.post_responses.append(FakeResponse(200, {"ok": True}))

        client.post.library.playlist_track("pl1", "t1")

        _, url, _, payload = fake_session.calls[0]
        assert url.endswith("/api/v1/library/playlists/pl1/tracks")
        assert payload == {"track_id": "t1"}

    def test_403_missing_scope_raises_forbidden(self, make_client, fake_session):
        client = make_client()
        fake_session.post_responses.append(FakeResponse(403, {"detail": "missing scope playlists:write"}))

        with pytest.raises(ForbiddenError):
            client.post.library.playlist("Roadtrip")

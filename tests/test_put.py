"""
Tests pour client.put.

Lancer avec : pytest tests/test_put.py -v
"""

from __future__ import annotations

import pytest

from VoltaLibPython.exceptions import APIError

from .conftest import FakeResponse


class TestPut:
    def test_put_request_success(self, make_client, fake_session):
        client = make_client()
        fake_session.put_responses.append(FakeResponse(200, {"updated": True}))

        result = client.put.request(
            "/api/v1/library/playlists/pl_123", {"name": "Roadtrip 2024"}
        )

        assert result == {"updated": True}
        method, url, headers, payload = fake_session.calls[0]
        assert method == "PUT"
        assert url.endswith("/api/v1/library/playlists/pl_123")
        assert payload == {"name": "Roadtrip 2024"}
        assert headers["Authorization"] == "Bearer initial_token"

    def test_put_401_refreshes_and_retries(self, make_client, fake_session):
        client = make_client({"access_token": "old_token", "expires_in": 3600})

        fake_session.put_responses.append(FakeResponse(401, text="invalid"))
        fake_session.post_responses.append(
            FakeResponse(200, {"access_token": "new_token", "expires_in": 3600})
        )
        fake_session.put_responses.append(FakeResponse(200, {"updated": True}))

        result = client.put.request(
            "/api/v1/library/playlists/pl_123", {"name": "Roadtrip 2024"}
        )

        assert result == {"updated": True}
        assert client.token == "new_token"

        put_calls = [c for c in fake_session.calls if c[0] == "PUT"]
        assert len(put_calls) == 2
        assert put_calls[0][2]["Authorization"] == "Bearer old_token"
        assert put_calls[1][2]["Authorization"] == "Bearer new_token"

    def test_put_401_twice_raises_after_single_retry(self, make_client, fake_session):
        client = make_client({"access_token": "old_token", "expires_in": 3600})

        fake_session.put_responses.append(FakeResponse(401, text="invalid"))
        fake_session.post_responses.append(
            FakeResponse(200, {"access_token": "new_token", "expires_in": 3600})
        )
        fake_session.put_responses.append(FakeResponse(401, text="invalid"))

        with pytest.raises(APIError):
            client.put.request("/api/v1/library/playlists/pl_123", {"name": "x"})

        put_calls = [c for c in fake_session.calls if c[0] == "PUT"]
        assert len(put_calls) == 2

    def test_put_non_200_raises_api_error(self, make_client, fake_session):
        client = make_client()
        fake_session.put_responses.append(FakeResponse(400, text="bad request"))

        with pytest.raises(APIError):
            client.put.request("/api/v1/library/playlists/pl_123", {"name": "x"})

    def test_put_sends_body_as_json(self, make_client, fake_session):
        client = make_client()
        fake_session.put_responses.append(FakeResponse(200, {"ok": True}))

        client.put.request(
            "/api/v1/library/playlists/pl_123/tracks/reorder",
            {"order": ["t1", "t2", "t3"]},
        )

        _, _, _, payload = fake_session.calls[0]
        assert payload == {"order": ["t1", "t2", "t3"]}

class TestPutLibrary:
    def test_playlist_sends_only_given_fields(self, make_client, fake_session):
        client = make_client()
        fake_session.put_responses.append(FakeResponse(200, {"updated": True}))

        client.put.library.playlist("pl1", name="Roadtrip 2024")

        method, url, _, payload = fake_session.calls[0]
        assert method == "PUT"
        assert url.endswith("/api/v1/library/playlists/pl1")
        assert payload == {"name": "Roadtrip 2024"}

    def test_playlist_visibility_false_is_sent(self, make_client, fake_session):
        client = make_client()
        fake_session.put_responses.append(FakeResponse(200, {"updated": True}))

        client.put.library.playlist("pl1", is_public=False)

        _, _, _, payload = fake_session.calls[0]
        assert payload == {"is_public": False}

    def test_playlist_without_fields_raises_before_request(self, make_client, fake_session):
        client = make_client()

        with pytest.raises(ValueError):
            client.put.library.playlist("pl1")

        assert fake_session.calls == []

    def test_reorder_sends_track_ids(self, make_client, fake_session):
        client = make_client()
        fake_session.put_responses.append(FakeResponse(200, {"ok": True}))

        client.put.library.reorder("pl1", ("t3", "t1", "t2"))

        _, url, _, payload = fake_session.calls[0]
        assert url.endswith("/api/v1/library/playlists/pl1/tracks/reorder")
        assert payload == {"track_ids": ["t3", "t1", "t2"]}

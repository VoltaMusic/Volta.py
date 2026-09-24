"""
Tests pour client.delete.

Lancer avec : pytest tests/test_delete.py -v
"""

from __future__ import annotations

import pytest

from VoltaLibPython.exceptions import APIError, NotFoundError

from .conftest import FakeResponse


class TestDelete:
    def test_delete_track_success(self, make_client, fake_session):
        client = make_client()
        fake_session.delete_responses.append(FakeResponse(200, {"deleted": True}))

        result = client.delete.library.track("t1")

        assert result == {"deleted": True}
        method, url, headers, _ = fake_session.calls[0]
        assert method == "DELETE"
        assert url.endswith("/api/v1/library/tracks/t1")
        assert headers["Authorization"] == "Bearer initial_token"

    def test_delete_401_refreshes_and_retries(self, make_client, fake_session):
        client = make_client({"access_token": "old_token", "expires_in": 3600})

        fake_session.delete_responses.append(FakeResponse(401, text="invalid"))
        fake_session.post_responses.append(
            FakeResponse(200, {"access_token": "new_token", "expires_in": 3600})
        )
        fake_session.delete_responses.append(FakeResponse(200, {"deleted": True}))

        result = client.delete.library.track("t1")

        assert result == {"deleted": True}
        assert client.token == "new_token"

    def test_delete_401_twice_raises_after_single_retry(self, make_client, fake_session):
        client = make_client({"access_token": "old_token", "expires_in": 3600})

        fake_session.delete_responses.append(FakeResponse(401, text="invalid"))
        fake_session.post_responses.append(
            FakeResponse(200, {"access_token": "new_token", "expires_in": 3600})
        )
        fake_session.delete_responses.append(FakeResponse(401, text="invalid"))

        with pytest.raises(APIError):
            client.delete.library.track("t1")

        delete_calls = [c for c in fake_session.calls if c[0] == "DELETE"]
        assert len(delete_calls) == 2

    def test_delete_non_200_raises_api_error(self, make_client, fake_session):
        client = make_client()
        fake_session.delete_responses.append(FakeResponse(404, text="not found"))

        with pytest.raises(APIError):
            client.delete.library.track("unknown_id")

    def test_delete_request_sends_body(self, make_client, fake_session):
        client = make_client()
        fake_session.delete_responses.append(FakeResponse(200, {"ok": True}))

        client.delete.request("/api/v1/library/playlists/pl1/tracks/t1", {"reason": "cleanup"})

        _, _, _, payload = fake_session.calls[0]
        assert payload == {"reason": "cleanup"}

    def test_delete_track_without_body_sends_no_json(self, make_client, fake_session):
        client = make_client()
        fake_session.delete_responses.append(FakeResponse(200, {"deleted": True}))

        client.delete.library.track("t1")

        _, _, _, payload = fake_session.calls[0]
        assert payload is None

class TestDeleteLibrary:
    @pytest.mark.parametrize(
        "method, args, path",
        [
            ("track", ("t1",), "/api/v1/library/tracks/t1"),
            ("album", ("al1",), "/api/v1/library/albums/al1"),
            ("artist", ("a1",), "/api/v1/library/artists/a1"),
            ("playlist", ("pl1",), "/api/v1/library/playlists/pl1"),
            ("playlist_track", ("pl1", "t1"), "/api/v1/library/playlists/pl1/tracks/t1"),
        ],
    )
    def test_hits_expected_url_without_body(self, make_client, fake_session, method, args, path):
        client = make_client()
        fake_session.delete_responses.append(FakeResponse(200, {"deleted": True}))

        result = getattr(client.delete.library, method)(*args)

        assert result == {"deleted": True}
        verb, url, _, payload = fake_session.calls[0]
        assert verb == "DELETE"
        assert url.endswith(path)
        assert payload is None

    def test_404_raises_not_found(self, make_client, fake_session):
        client = make_client()
        fake_session.delete_responses.append(FakeResponse(404, {"detail": "playlist not found"}))

        with pytest.raises(NotFoundError):
            client.delete.library.playlist("unknown")

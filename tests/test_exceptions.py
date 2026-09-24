"""
Tests des exceptions : chaque erreur possible (HTTP, réseau, réponse
invalide, fichier de token, argument invalide) doit remonter sous la forme
d'une exception de la lib, jamais d'une exception brute de `requests`,
`json` ou `os`.

Lancer avec : pytest tests/test_exceptions.py -v
"""

from __future__ import annotations

import json

import pytest
import requests

from VoltaLibPython.client import VoltaClient
from VoltaLibPython.exceptions import (
    APIError,
    ConflictError,
    ConnectionFailedError,
    InvalidArgumentError,
    InvalidResponseError,
    NetworkError,
    RateLimitError,
    RequestTimeoutError,
    ServerError,
    TokenStorageError,
    UnprocessableEntityError,
    VoltaAPIExceptions,
)

from .conftest import FakeResponse, FakeSession


def _raising(exc: Exception):
    def send(*args, **kwargs):
        raise exc
    return send


# ---------------------------------------------------------------------------
# Hiérarchie
# ---------------------------------------------------------------------------

class TestHierarchy:
    @pytest.mark.parametrize(
        "cls",
        [
            ConflictError, ConnectionFailedError, InvalidArgumentError, InvalidResponseError,
            NetworkError, RateLimitError, RequestTimeoutError, ServerError, TokenStorageError,
            UnprocessableEntityError,
        ],
    )
    def test_every_exception_inherits_from_base(self, cls):
        assert issubclass(cls, VoltaAPIExceptions)

    def test_invalid_argument_is_still_a_value_error(self):
        # Le code qui attrapait ValueError avant continue de fonctionner.
        assert issubclass(InvalidArgumentError, ValueError)

    def test_network_errors_share_a_base(self):
        assert issubclass(RequestTimeoutError, NetworkError)
        assert issubclass(ConnectionFailedError, NetworkError)
        assert not issubclass(NetworkError, APIError)


# ---------------------------------------------------------------------------
# Codes HTTP
# ---------------------------------------------------------------------------

class TestHttpErrors:
    def test_409_raises_conflict_error(self, make_client, fake_session):
        client = make_client()
        fake_session.post_responses.append(FakeResponse(409, {"detail": "already in library"}))

        with pytest.raises(ConflictError) as exc:
            client.post.library.track({"id": "t1", "name": "X", "artist": "Y", "album": "Z"})

        assert exc.value.status_code == 409
        assert exc.value.detail == "already in library"

    def test_422_validation_detail_is_readable(self, make_client, fake_session):
        client = make_client()
        fake_session.post_responses.append(
            FakeResponse(422, {"detail": [
                {"loc": ["body", "track_id"], "msg": "field required", "type": "missing"},
                {"loc": ["body", "name"], "msg": "too long", "type": "value_error"},
            ]})
        )

        with pytest.raises(UnprocessableEntityError) as exc:
            client.post.library.playlist("x")

        assert exc.value.detail == "track_id : field required ; name : too long"
        assert "[422]" in str(exc.value)

    def test_429_exposes_retry_after(self, make_client, fake_session):
        client = make_client()
        response = FakeResponse(429, {"detail": "slow down"})
        response.headers = {"Retry-After": "12"}
        fake_session.get_responses.append(response)

        with pytest.raises(RateLimitError) as exc:
            client.get.library.tracks()

        assert exc.value.retry_after == 12
        assert "12 s" in str(exc.value)

    def test_429_without_header_has_no_retry_after(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(429, text="too many"))

        with pytest.raises(RateLimitError) as exc:
            client.get.library.tracks()

        assert exc.value.retry_after is None

    def test_503_raises_server_error(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(503, {"detail": "not configured"}))

        with pytest.raises(ServerError):
            client.get.catalog.home()

    def test_unknown_status_raises_generic_api_error(self, make_client, fake_session):
        client = make_client()
        fake_session.get_responses.append(FakeResponse(418, text="teapot"))

        with pytest.raises(APIError) as exc:
            client.get.catalog.home()

        assert type(exc.value) is APIError


# ---------------------------------------------------------------------------
# Erreurs réseau
# ---------------------------------------------------------------------------

class TestNetworkErrors:
    @pytest.mark.parametrize("verb", ["get", "post", "put", "delete"])
    def test_timeout_raises_request_timeout_error(self, make_client, fake_session, monkeypatch, verb):
        client = make_client()
        original = requests.exceptions.ReadTimeout("read timed out")
        monkeypatch.setattr(fake_session, verb, _raising(original))

        with pytest.raises(RequestTimeoutError) as exc:
            client._request(verb.upper(), "/api/v1/home", data={})

        assert exc.value.__cause__ is original
        assert exc.value.url.endswith("/api/v1/home")

    def test_connection_error_raises_connection_failed_error(self, make_client, fake_session, monkeypatch):
        client = make_client()
        monkeypatch.setattr(fake_session, "get", _raising(requests.exceptions.ConnectionError("refused")))

        with pytest.raises(ConnectionFailedError):
            client.get.library.tracks()

    def test_ssl_error_raises_connection_failed_error(self, make_client, fake_session, monkeypatch):
        client = make_client()
        monkeypatch.setattr(fake_session, "get", _raising(requests.exceptions.SSLError("bad cert")))

        with pytest.raises(ConnectionFailedError):
            client.get.library.tracks()

    def test_other_request_exception_raises_network_error(self, make_client, fake_session, monkeypatch):
        client = make_client()
        monkeypatch.setattr(fake_session, "get", _raising(requests.exceptions.TooManyRedirects("loop")))

        with pytest.raises(NetworkError) as exc:
            client.get.library.tracks()

        assert type(exc.value) is NetworkError
        assert "TooManyRedirects" in str(exc.value)

    def test_token_refresh_network_error_is_wrapped(self, tmp_path, monkeypatch):
        session = FakeSession()
        monkeypatch.setattr(session, "post", _raising(requests.exceptions.ConnectTimeout("timeout")))
        monkeypatch.setattr("VoltaLibPython.client._build_session", lambda: session)

        with pytest.raises(RequestTimeoutError):
            VoltaClient(token_file=str(tmp_path / "token.json"))


# ---------------------------------------------------------------------------
# Réponse invalide du endpoint de token
# ---------------------------------------------------------------------------

class _NotJsonResponse(FakeResponse):
    def json(self):
        raise ValueError("Expecting value")


class TestInvalidTokenResponse:
    def _client_with_token_response(self, tmp_path, monkeypatch, response):
        session = FakeSession()
        session.post_responses.append(response)
        monkeypatch.setattr("VoltaLibPython.client._build_session", lambda: session)
        return VoltaClient(token_file=str(tmp_path / "token.json"))

    def test_non_json_token_response(self, tmp_path, monkeypatch):
        with pytest.raises(InvalidResponseError, match="pas du JSON") as exc:
            self._client_with_token_response(
                tmp_path, monkeypatch, _NotJsonResponse(200, text="<html>maintenance</html>")
            )
        assert "maintenance" in str(exc.value)

    def test_token_response_without_access_token(self, tmp_path, monkeypatch):
        with pytest.raises(InvalidResponseError, match="access_token"):
            self._client_with_token_response(tmp_path, monkeypatch, FakeResponse(200, {"expires_in": 3600}))

    def test_token_response_with_invalid_expires_in(self, tmp_path, monkeypatch):
        with pytest.raises(InvalidResponseError):
            self._client_with_token_response(
                tmp_path, monkeypatch, FakeResponse(200, {"access_token": "tok", "expires_in": "soon"})
            )

    def test_invalid_token_response_is_not_saved(self, tmp_path, monkeypatch):
        with pytest.raises(InvalidResponseError):
            self._client_with_token_response(tmp_path, monkeypatch, FakeResponse(200, {"foo": "bar"}))
        assert not (tmp_path / "token.json").exists()


# ---------------------------------------------------------------------------
# Fichier de token
# ---------------------------------------------------------------------------

class TestTokenFile:
    @pytest.mark.parametrize("content", ["{not json", "[]", '{"expires_in": 3600}', ""])
    def test_corrupted_token_file_triggers_refresh(self, tmp_path, monkeypatch, content):
        token_file = tmp_path / "token.json"
        token_file.write_text(content)
        session = FakeSession()
        session.post_responses.append(FakeResponse(200, {"access_token": "fresh", "expires_in": 3600}))
        monkeypatch.setattr("VoltaLibPython.client._build_session", lambda: session)

        client = VoltaClient(token_file=str(token_file))
        try:
            assert client.token == "fresh"
            assert json.loads(token_file.read_text())["access_token"] == "fresh"
        finally:
            client.stop_background_refresh()

    def test_unwritable_token_file_raises_token_storage_error(self, tmp_path, monkeypatch):
        # Le chemin du fichier de token est un dossier : impossible d'y écrire.
        token_dir = tmp_path / "token.json"
        token_dir.mkdir()
        session = FakeSession()
        session.post_responses.append(FakeResponse(200, {"access_token": "tok", "expires_in": 3600}))
        monkeypatch.setattr("VoltaLibPython.client._build_session", lambda: session)

        with pytest.raises(TokenStorageError) as exc:
            VoltaClient(token_file=str(token_dir))

        assert exc.value.path == str(token_dir)
        assert isinstance(exc.value.__cause__, OSError)


# ---------------------------------------------------------------------------
# Arguments invalides
# ---------------------------------------------------------------------------

class TestInvalidArguments:
    def test_playlists_search_and_id(self, make_client, fake_session):
        client = make_client()
        with pytest.raises(InvalidArgumentError, match="search"):
            client.get.library.playlists(search="x", id="pl1")
        assert fake_session.calls == []

    def test_create_playlist_without_name(self, make_client, fake_session):
        client = make_client()
        with pytest.raises(InvalidArgumentError, match="name"):
            client.post.library.playlist("")
        assert fake_session.calls == []

    def test_update_playlist_without_fields(self, make_client, fake_session):
        client = make_client()
        with pytest.raises(InvalidArgumentError):
            client.put.library.playlist("pl1")
        assert fake_session.calls == []

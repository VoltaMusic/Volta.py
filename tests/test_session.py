"""
Tests de la politique de retry de la session HTTP.

Lancer avec : pytest tests/test_session.py -v
"""

from __future__ import annotations

import json

import pytest

from VoltaLibPython.client import VoltaClient
from VoltaLibPython.session import _build_session, _mount_token_retry

from .conftest import FakeSession

BASE_URL = "https://api.volta-music.test"


def _allowed_methods(session, url):
    return session.get_adapter(url).max_retries.allowed_methods


@pytest.fixture
def session():
    s = _build_session()
    _mount_token_retry(s, BASE_URL)
    yield s
    s.close()


class TestRetryPolicy:
    def test_get_is_retried(self, session):
        assert "GET" in _allowed_methods(session, f"{BASE_URL}/api/v1/library/tracks")

    @pytest.mark.parametrize("method", ["POST", "PUT", "DELETE"])
    def test_writes_are_never_retried(self, session, method):
        # Un 5xx peut arriver après que le serveur a déjà créé la ressource :
        # rejouer la requête créerait un doublon.
        for path in ("/api/v1/library/playlists", "/api/v1/library/tracks", "/api/v1/library/playlists/pl1"):
            assert method not in _allowed_methods(session, f"{BASE_URL}{path}")

    def test_token_post_is_retried(self, session):
        assert "POST" in _allowed_methods(session, f"{BASE_URL}/api/v1/oauth/token")

    def test_token_adapter_only_applies_to_token_endpoint(self, session):
        assert "POST" not in _allowed_methods(session, f"{BASE_URL}/api/v1/oauth")
        assert "POST" not in _allowed_methods(session, "https://other-host.test/api/v1/oauth/token")

    def test_trailing_slash_in_base_url(self):
        s = _build_session()
        _mount_token_retry(s, BASE_URL + "/")
        try:
            assert "POST" in _allowed_methods(s, f"{BASE_URL}/api/v1/oauth/token")
        finally:
            s.close()

    def test_client_mounts_token_retry_on_its_base_url(self, tmp_path, monkeypatch):
        fake = FakeSession()
        monkeypatch.setattr("VoltaLibPython.client._build_session", lambda: fake)
        token_file = tmp_path / "token.json"
        token_file.write_text(json.dumps({"access_token": "tok", "expires_in": 3600}))

        client = VoltaClient(base_url=BASE_URL, token_file=str(token_file))
        try:
            adapter = fake.mounted.get(f"{BASE_URL}/api/v1/oauth/token")
            assert adapter is not None
            assert "POST" in adapter.max_retries.allowed_methods
        finally:
            client.stop_background_refresh()

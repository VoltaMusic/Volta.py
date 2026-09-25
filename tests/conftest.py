"""
Fixtures partagées pour les tests de VoltaClient.

Aucune requête réseau réelle n'est faite : `VoltaClient._session` est
remplacée par une fausse session (`FakeSession`) dont on contrôle
entièrement les réponses, dans l'ordre où elles doivent être renvoyées.

Adapter si besoin :
- Le chemin d'import `from VoltaLibPython.client import VoltaClient`
  suppose que ces tests tournent depuis la racine du projet, avec un
  package `VoltaLibPython` contenant `client.py` et `exceptions.py`.
  Si ton package s'appelle autrement, ajuste l'import dans ce fichier
  et dans test_volta_client.py.
"""

from __future__ import annotations

import json
from typing import Any, Optional

import pytest

from VoltaLibPython.client import VoltaClient


class FakeResponse:
    """Imite juste ce que le client utilise d'une `requests.Response`.

    `url` reflète l'URL réellement appelée — comme le vrai
    `requests.Response.url` — et est renseigné par `FakeSession` au moment
    où la réponse est renvoyée (voir plus bas), pas à la construction :
    au moment où le test crée `FakeResponse(...)`, on ne sait pas encore
    sur quelle URL elle sera utilisée.
    """

    def __init__(self, status_code: int, json_data: Optional[dict] = None, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data if json_data is not None else {}
        self.text = text or json.dumps(self._json_data)
        self.url: Optional[str] = None

    def json(self) -> Any:
        return self._json_data


class FakeSession:
    """Remplace `requests.Session` : on empile les réponses à renvoyer pour
    chaque verbe HTTP, et on enregistre chaque appel pour vérification."""

    def __init__(self) -> None:
        self.get_responses: list[FakeResponse] = []
        self.post_responses: list[FakeResponse] = []
        self.put_responses: list[FakeResponse] = []
        self.delete_responses: list[FakeResponse] = []
        self.calls: list[tuple] = []  # (method, url, headers, payload)
        self.closed = False
        self.mounted: dict = {}

    def get(self, url, headers=None, params=None, timeout=None):
        self.calls.append(("GET", url, headers, params))
        if not self.get_responses:
            raise AssertionError(f"Aucune réponse GET simulée en attente pour {url}")
        response = self.get_responses.pop(0)
        response.url = url
        return response

    def post(self, url, headers=None, json=None, data=None, timeout=None):
        payload = json if json is not None else data
        self.calls.append(("POST", url, headers, payload))
        if not self.post_responses:
            raise AssertionError(f"Aucune réponse POST simulée en attente pour {url}")
        response = self.post_responses.pop(0)
        response.url = url
        return response

    def put(self, url, headers=None, json=None, timeout=None):
        self.calls.append(("PUT", url, headers, json))
        if not self.put_responses:
            raise AssertionError(f"Aucune réponse PUT simulée en attente pour {url}")
        response = self.put_responses.pop(0)
        response.url = url
        return response

    def delete(self, url, headers=None, json=None, timeout=None):
        self.calls.append(("DELETE", url, headers, json))
        if not self.delete_responses:
            raise AssertionError(f"Aucune réponse DELETE simulée en attente pour {url}")
        response = self.delete_responses.pop(0)
        response.url = url
        return response

    def close(self) -> None:
        self.closed = True

    def mount(self, prefix, adapter) -> None:
        self.mounted[prefix] = adapter


@pytest.fixture(autouse=True)
def fake_credentials(monkeypatch):
    """Fournit de faux CLIENT_ID / CLIENT_SECRET à tous les tests.

    Sans ça, les tests dépendraient du `.env` local : ils passent sur ta
    machine mais échouent en CI (ConfigurationError avant même que la
    FakeSession ne réponde)."""
    monkeypatch.setenv("CLIENT_ID", "test_client_id")
    monkeypatch.setenv("CLIENT_SECRET", "test_client_secret")


@pytest.fixture
def fake_session() -> FakeSession:
    return FakeSession()


@pytest.fixture
def make_client(tmp_path, monkeypatch, fake_session):
    """Fabrique un VoltaClient sans jamais toucher le réseau.

    - `_load_token` est patché pour renvoyer directement un token en
      mémoire (pas de fichier existant à lire, pas de refresh initial).
    - La session interne est remplacée par `fake_session` juste après
      construction.
    - Tous les clients créés sont proprement fermés (`close`)
      à la fin du test pour ne laisser traîner aucun thread.
    """
    created: list[VoltaClient] = []

    def _make(token_data: Optional[dict] = None) -> VoltaClient:
        token_data = token_data or {"access_token": "initial_token", "expires_in": 3600}
        monkeypatch.setattr(VoltaClient, "_load_token", lambda self: dict(token_data))
        client = VoltaClient(
            base_url="https://api.volta-music.test",
            token_file=str(tmp_path / "token.json"),
        )
        client._session = fake_session
        created.append(client)
        return client

    yield _make

    for client in created:
        client.close()
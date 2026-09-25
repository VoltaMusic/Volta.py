"""
Tests du cycle de vie de VoltaClient : chargement/sauvegarde du token,
arrêt du thread de fond, context manager. Ces tests ne sont pas liés à un
verbe HTTP en particulier (contrairement à test_get_*.py, test_post.py,
test_put.py et test_delete.py).

Lancer avec : pytest tests/test_client_lifecycle.py -v
"""

from __future__ import annotations

import json
import os
import textwrap
import time

import pytest

from VoltaLibPython.client import VoltaClient
from VoltaLibPython.exceptions import ConfigurationError

from .conftest import FakeResponse


class TestTokenLoading:
    def test_load_token_reads_existing_file_without_network_call(
        self, tmp_path, monkeypatch, fake_session
    ):
        token_file = tmp_path / "token.json"
        token_file.write_text(json.dumps({"access_token": "from_disk", "expires_in": 1200}))

        client = VoltaClient(token_file=str(token_file))
        client._session = fake_session
        try:
            assert client.token == "from_disk"
            # Ancien format sans expires_at : échéance = date du fichier + expires_in.
            assert 1190 <= client.refresh_interval <= 1200
            # Aucun appel réseau n'a dû être fait pour charger un token déjà présent.
            assert fake_session.calls == []
        finally:
            client.stop_background_refresh()

    def test_load_token_triggers_refresh_when_file_missing(self, tmp_path, monkeypatch):
        token_file = tmp_path / "does_not_exist" / "token.json"

        # On patche _build_session pour injecter notre fausse session AVANT
        # que __init__ ne s'en serve pour aller chercher le premier token.
        from tests.conftest import FakeSession

        session = FakeSession()
        session.post_responses.append(
            FakeResponse(200, {"access_token": "brand_new", "expires_in": 3600})
        )
        monkeypatch.setattr("VoltaLibPython.client._build_session", lambda: session)

        client = VoltaClient(token_file=str(token_file))
        try:
            assert client.token == "brand_new"
            assert token_file.exists()  # le token obtenu a bien été persisté
            saved = json.loads(token_file.read_text())
            assert saved["access_token"] == "brand_new"
        finally:
            client.stop_background_refresh()

    def test_missing_credentials_raise_configuration_error_without_network_call(
        self, tmp_path, monkeypatch
    ):
        from tests.conftest import FakeSession

        session = FakeSession()
        monkeypatch.setattr("VoltaLibPython.client._build_session", lambda: session)
        monkeypatch.setenv("CLIENT_SECRET", "")

        with pytest.raises(ConfigurationError, match="CLIENT_SECRET"):
            VoltaClient(token_file=str(tmp_path / "token.json"))
        # L'erreur doit être levée avant d'appeler l'API.
        assert session.calls == []


def _client_with_session(tmp_path, monkeypatch, token_file, *responses):
    from tests.conftest import FakeSession

    session = FakeSession()
    session.post_responses.extend(responses)
    monkeypatch.setattr("VoltaLibPython.client._build_session", lambda: session)
    return VoltaClient(token_file=str(token_file) if token_file else None), session


class TestTokenExpiry:
    def test_refreshed_token_is_saved_with_absolute_expiry(self, tmp_path, monkeypatch):
        token_file = tmp_path / "token.json"
        before = time.time()
        client, _ = _client_with_session(
            tmp_path, monkeypatch, token_file, FakeResponse(200, {"access_token": "new", "expires_in": 3600})
        )
        client.close()

        saved = json.loads(token_file.read_text())
        assert int(before) + 3600 <= saved["expires_at"] <= time.time() + 3600

    def test_valid_token_file_is_reused_without_network_call(self, tmp_path, monkeypatch):
        token_file = tmp_path / "token.json"
        token_file.write_text(json.dumps(
            {"access_token": "on_disk", "expires_in": 3600, "expires_at": time.time() + 600}
        ))
        client, session = _client_with_session(tmp_path, monkeypatch, token_file)
        try:
            assert client.token == "on_disk"
            assert 590 <= client.refresh_interval <= 600
            assert session.calls == []
        finally:
            client.close()

    def test_expired_token_file_triggers_refresh(self, tmp_path, monkeypatch):
        token_file = tmp_path / "token.json"
        token_file.write_text(json.dumps(
            {"access_token": "stale", "expires_in": 3600, "expires_at": time.time() - 60}
        ))
        client, session = _client_with_session(
            tmp_path, monkeypatch, token_file, FakeResponse(200, {"access_token": "fresh", "expires_in": 3600})
        )
        try:
            assert client.token == "fresh"
            assert len(session.calls) == 1
        finally:
            client.close()

    def test_legacy_file_older_than_its_expires_in_triggers_refresh(self, tmp_path, monkeypatch):
        # Ancien format : expires_in relatif, écrit il y a 2 h. Le jeton est
        # périmé même si expires_in vaut encore 3600.
        token_file = tmp_path / "token.json"
        token_file.write_text(json.dumps({"access_token": "stale", "expires_in": 3600}))
        two_hours_ago = time.time() - 7200
        os.utime(token_file, (two_hours_ago, two_hours_ago))

        client, session = _client_with_session(
            tmp_path, monkeypatch, token_file, FakeResponse(200, {"access_token": "fresh", "expires_in": 3600})
        )
        try:
            assert client.token == "fresh"
        finally:
            client.close()

    def test_close_does_not_rewrite_token_file(self, tmp_path, monkeypatch):
        token_file = tmp_path / "token.json"
        content = json.dumps({"access_token": "tok", "expires_in": 3600, "expires_at": time.time() + 3600})
        token_file.write_text(content)
        client, _ = _client_with_session(tmp_path, monkeypatch, token_file)
        client.close()
        assert token_file.read_text() == content


class TestStop:

    def test_stop_background_refresh_is_idempotent(self, make_client):
        client = make_client()
        client.stop_background_refresh()
        # Un second appel ne doit ni lever d'exception ni re-sauvegarder.
        client.stop_background_refresh()  # ne doit pas planter

    def test_context_manager_stops_refresh_and_closes_session(
        self, tmp_path, monkeypatch, fake_session
    ):
        token_data = {"access_token": "tok", "expires_in": 3600}
        monkeypatch.setattr(VoltaClient, "_load_token", lambda self: dict(token_data))

        with VoltaClient(token_file=str(tmp_path / "token.json")) as client:
            client._session = fake_session
            assert client._closed is False

        assert client._closed is True
        assert fake_session.closed is True


class TestTokenThreadSafety:
    def test_auth_headers_reflects_token_after_manual_refresh(self, make_client, fake_session):
        client = make_client({"access_token": "old_token", "expires_in": 3600})
        assert client._auth_headers()["Authorization"] == "Bearer old_token"

        fake_session.post_responses.append(
            FakeResponse(200, {"access_token": "manually_refreshed", "expires_in": 3600})
        )
        client._handle_unauthorized()

        assert client._auth_headers()["Authorization"] == "Bearer manually_refreshed"

class TestDefaults:
    def test_spinner_is_disabled_by_default(self, make_client):
        client = make_client()
        assert client.show_progress is False


class TestCredentials:
    def test_arguments_take_priority_over_environment(self, tmp_path, monkeypatch):
        from tests.conftest import FakeSession

        session = FakeSession()
        session.post_responses.append(FakeResponse(200, {"access_token": "tok", "expires_in": 3600}))
        monkeypatch.setattr("VoltaLibPython.client._build_session", lambda: session)

        client = VoltaClient(
            token_file=str(tmp_path / "token.json"), client_id="arg_id", client_secret="arg_secret"
        )
        try:
            _, _, _, payload = session.calls[0]
            assert payload["client_id"] == "arg_id"
            assert payload["client_secret"] == "arg_secret"
        finally:
            client.stop_background_refresh()

    def test_environment_is_used_when_no_argument_is_given(self, make_client):
        client = make_client()
        assert client.client_id == "test_client_id"
        assert client.client_secret == "test_client_secret"


class TestDotenv:
    def test_import_does_not_load_dotenv(self, tmp_path):
        import os
        import subprocess
        import sys

        (tmp_path / ".env").write_text("VOLTA_DOTENV_PROBE=loaded")
        code = "import os, VoltaLibPython; print(os.environ.get('VOLTA_DOTENV_PROBE', 'absent'))"
        env = {**os.environ, "PYTHONPATH": os.getcwd()}
        env.pop("VOLTA_DOTENV_PROBE", None)
        out = subprocess.run(
            [sys.executable, "-c", code], cwd=tmp_path, env=env, capture_output=True, text=True, check=True
        )
        assert out.stdout.strip() == "absent"

    def test_dotenv_not_read_when_credentials_are_given(self, tmp_path, monkeypatch):
        calls = []
        monkeypatch.setattr("VoltaLibPython.client.load_dotenv", lambda *a, **k: calls.append(1))
        monkeypatch.setattr(VoltaClient, "_load_token", lambda self: {"access_token": "t", "expires_in": 3600})

        client = VoltaClient(token_file=str(tmp_path / "token.json"), client_id="id", client_secret="secret")
        client.stop_background_refresh()
        assert calls == []

    def test_dotenv_read_when_a_credential_is_missing(self, tmp_path, monkeypatch):
        calls = []
        monkeypatch.setattr("VoltaLibPython.client.load_dotenv", lambda *a, **k: calls.append(1))
        monkeypatch.setattr(VoltaClient, "_load_token", lambda self: {"access_token": "t", "expires_in": 3600})

        client = VoltaClient(token_file=str(tmp_path / "token.json"))
        client.stop_background_refresh()
        assert calls == [1]


class TestClose:
    def test_close_stops_refresh_and_closes_session(self, make_client, fake_session):
        client = make_client()
        client.close()
        assert client._closed is True
        assert client._refresh_timer is None
        assert fake_session.closed is True

    def test_close_is_idempotent(self, make_client):
        client = make_client()
        client.close()
        client.close()  # ne doit pas planter


class TestAtexit:
    def test_client_is_closed_at_program_exit(self, tmp_path):
        import os
        import subprocess
        import sys

        token_file = tmp_path / "token.json"
        token_file.write_text(json.dumps({"access_token": "tok", "expires_in": 3600}))
        # Client jamais fermé : atexit doit appeler close().
        code = textwrap.dedent(f"""
            from VoltaLibPython import VoltaClient
            original = VoltaClient.close
            def close(self):
                print('closed')
                original(self)
            VoltaClient.close = close
            VoltaClient(token_file={str(token_file)!r}, client_id='id', client_secret='secret')
        """)
        env = {**os.environ, "PYTHONPATH": os.getcwd()}
        out = subprocess.run(
            [sys.executable, "-c", code], cwd=tmp_path, env=env, capture_output=True, text=True, check=True
        )
        assert out.stdout.strip() == "closed"

    def test_close_unregisters_atexit_hook(self, make_client, monkeypatch):
        import atexit

        unregistered = []
        monkeypatch.setattr(atexit, "unregister", lambda func: unregistered.append(func))
        client = make_client()
        client.close()
        assert unregistered == [client.close]


class TestDefaultTokenFile:
    def _default(self, monkeypatch, tmp_path, client_id):
        from VoltaLibPython.client import _default_token_file

        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
        return _default_token_file(client_id)

    def test_default_is_in_user_cache_folder(self, monkeypatch, tmp_path):
        path = self._default(monkeypatch, tmp_path, "id")
        assert os.path.dirname(path) == os.path.join(str(tmp_path), "voltalib")
        assert "id" not in os.path.basename(path)  # l'ID client n'apparaît pas en clair

    def test_each_client_id_gets_its_own_file(self, monkeypatch, tmp_path):
        assert self._default(monkeypatch, tmp_path, "a") != self._default(monkeypatch, tmp_path, "b")
        assert self._default(monkeypatch, tmp_path, "a") == self._default(monkeypatch, tmp_path, "a")

    def test_client_uses_default_when_token_file_not_given(self, monkeypatch, tmp_path):
        from VoltaLibPython.client import _default_token_file

        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
        client, _ = _client_with_session(
            tmp_path, monkeypatch, None, FakeResponse(200, {"access_token": "tok", "expires_in": 3600})
        )
        try:
            assert client.token_file == _default_token_file("test_client_id")
            assert os.path.exists(client.token_file)
        finally:
            client.close()

    @pytest.mark.skipif(os.name == "nt", reason="Windows ignore les droits POSIX")
    def test_token_file_is_private(self, tmp_path, monkeypatch):
        token_file = tmp_path / "token.json"
        token_file.write_text("{}")
        os.chmod(token_file, 0o644)
        client, _ = _client_with_session(
            tmp_path, monkeypatch, token_file, FakeResponse(200, {"access_token": "tok", "expires_in": 3600})
        )
        client.close()
        assert os.stat(token_file).st_mode & 0o777 == 0o600

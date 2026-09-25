from __future__ import annotations

import atexit
import contextlib
import hashlib
import json
import logging
import os
import threading
import time
from typing import Any, Optional

import requests
from dotenv import load_dotenv

from .endpoints.verbs import Delete, Get, Post, Put
from .exceptions import (
    ConfigurationError,
    ConnectionFailedError,
    InvalidResponseError,
    NetworkError,
    RequestTimeoutError,
    TokenStorageError,
    error_from_response,
)
from .progress import _Spinner
from .session import (
    DEFAULT_TIMEOUT,
    TOKEN_ENDPOINT,
    TOKEN_REFRESH_MARGIN,
    _build_session,
    _mount_token_retry,
)

logger = logging.getLogger(__name__)


class VoltaClient:
    def __init__(
        self,
        base_url: str = "https://api.volta-music.com",
        token_file: Optional[str] = None,
        show_progress: bool = False,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ) -> None:
        self.base_url = base_url
        # Les identifiants passés en argument priment sur l'environnement.
        # Le .env n'est lu qu'ici, et seulement s'il manque quelque chose :
        # importer la lib ne modifie jamais os.environ.
        if not (client_id and client_secret):
            load_dotenv()
        self.client_id = client_id or os.getenv("CLIENT_ID")
        self.client_secret = client_secret or os.getenv("CLIENT_SECRET")
        self.token_file = token_file or _default_token_file(self.client_id)
        self.show_progress = show_progress

        self._session = _build_session()
        _mount_token_retry(self._session, self.base_url)
        self._token_lock = threading.Lock()
        self._refresh_timer: Optional[threading.Timer] = None
        self._closed = False

        self.token_data: dict[str, Any] = self._load_token()
        self.token: Optional[str] = self.token_data.get("access_token")
        self.refresh_interval: int = _seconds_left(self.token_data)

        self._start_background_refresh()
        # Filet de sécurité si le client n'est ni utilisé avec `with` ni
        # fermé à la main : il est quand même fermé proprement à la fin du
        # programme.
        atexit.register(self.close)

        self.get = Get(self)
        self.post = Post(self)
        self.put = Put(self)
        self.delete = Delete(self)

    # -- Gestion du token -------------------------------------------------

    def _refresh_token(self) -> dict[str, Any]:
        missing = [name for name, value in (("CLIENT_ID", self.client_id), ("CLIENT_SECRET", self.client_secret)) if not value]
        if missing:
            raise ConfigurationError(
                f"{' and '.join(missing)} missing. Pass them to VoltaClient(client_id=..., client_secret=...) "
                "or add them to the .env file at the root of your project "
                "(and check that an empty environment variable with the same name isn't hiding them)."
            )
        url = f"{self.base_url}{TOKEN_ENDPOINT}"
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        response = self._send(self._session.post, url, data=payload, timeout=DEFAULT_TIMEOUT)
        if response.status_code != 200:
            raise error_from_response(
                response.status_code, response.text, "Token refresh failed",
                headers=getattr(response, "headers", None),
            )
        try:
            token_data = response.json()
        except ValueError as e:
            raise InvalidResponseError(
                "Token refresh failed: the API response is not JSON",
                response_text=response.text,
            ) from e
        if not _is_valid_token_data(token_data):
            raise InvalidResponseError(
                "Token refresh failed: `access_token` or `expires_in` missing or invalid",
                response_text=response.text,
            )
        # Échéance absolue : contrairement à `expires_in`, elle reste juste
        # quand le fichier est relu plus tard par un autre lancement.
        token_data = {**token_data, "expires_at": int(time.time()) + int(token_data.get("expires_in", 3600))}
        self._save_token(token_data)
        return token_data

    def _save_token(self, token_data: dict[str, Any]) -> None:
        try:
            directory = os.path.dirname(self.token_file)
            if directory:
                os.makedirs(directory, exist_ok=True)
            # Lisible par l'utilisateur seul : le fichier contient un jeton
            # d'accès en clair (sans effet sous Windows, qui ignore ces droits).
            fd = os.open(self.token_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as f:
                json.dump(token_data, f, indent=4)
            os.chmod(self.token_file, 0o600)  # fichier déjà existant, créé avec d'autres droits
        except OSError as e:
            raise TokenStorageError(
                f"Cannot write the token file ({e.strerror or e})", path=self.token_file
            ) from e

    def _load_token(self) -> dict[str, Any]:
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, "r") as f:
                    token_data = json.load(f)
            except OSError as e:
                raise TokenStorageError(
                    f"Cannot read the token file ({e.strerror or e})", path=self.token_file
                ) from e
            except ValueError:
                token_data = None
            if _is_valid_token_data(token_data):
                if "expires_at" not in token_data:
                    # Ancien format (expires_in seul) : on part de la date de
                    # dernière écriture du fichier.
                    expires_at = os.path.getmtime(self.token_file) + int(token_data.get("expires_in", 3600))
                    token_data["expires_at"] = int(expires_at)
                if _seconds_left(token_data) > TOKEN_REFRESH_MARGIN:
                    return token_data
                logger.info("Token expired (%s), requesting a new one.", self.token_file)
            else:
                # Fichier corrompu ou incomplet : pas une raison de planter, on
                # redemande simplement un jeton (qui réécrira le fichier).
                logger.warning("Invalid token file (%s), requesting a new token.", self.token_file)
        return self._refresh_token()

    def _start_background_refresh(self) -> None:
        if self._refresh_timer is not None:
            self._refresh_timer.cancel()
        delay = max(self.refresh_interval - TOKEN_REFRESH_MARGIN, 1)
        self._refresh_timer = threading.Timer(delay, self._background_refresh_tick)
        self._refresh_timer.daemon = True
        self._refresh_timer.start()

    def _background_refresh_tick(self) -> None:
        try:
            token_data = self._refresh_token()
            with self._token_lock:
                self.token_data = token_data
                self.token = token_data.get("access_token")
                self.refresh_interval = _seconds_left(token_data)
        except Exception:
            logger.exception("Token refresh failed; retrying in 30s")
            self.refresh_interval = 30
        if not self._closed:
            self._start_background_refresh()

    def stop_background_refresh(self) -> None:
        if self._closed:
            return  # déjà arrêté (ex. close() puis __exit__)
        self._closed = True
        if self._refresh_timer is not None:
            self._refresh_timer.cancel()
            self._refresh_timer = None

    def close(self) -> None:
        """Stop the automatic token refresh and close the HTTP session.
        Safe to call several times."""
        atexit.unregister(self.close)  # plus rien à faire à la sortie du programme
        self.stop_background_refresh()
        self._session.close()

    def __enter__(self) -> "VoltaClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def _auth_headers(self) -> dict[str, str]:
        with self._token_lock:
            token = self.token
        return {"Authorization": f"Bearer {token}"}

    def _progress(self, message: str):
        """Contexte à utiliser autour de l'appel réseau : affiche un
        spinner si `show_progress` est activé, sinon ne fait rien."""
        if not self.show_progress:
            return contextlib.nullcontext()
        return _Spinner(message)

    # -- Rafraîchissement suite à un 401 ------------------------------------

    def _handle_response(self, response: requests.Response) -> Any:
        """
        Analyse la réponse HTTP et lève l'exception spécifique adaptée.
        """
        if 200 <= response.status_code < 300:
            try:
                return response.json()
            except ValueError:
                return response.text

        raise error_from_response(
            response.status_code, response.text, f"Request to {response.url} failed",
            headers=getattr(response, "headers", None),
        )

    def _handle_unauthorized(self) -> None:
        """Force un nouveau jeton suite à un 401 (jeton invalide/expiré côté
        serveur avant même notre propre échéance de refresh), de façon
        thread-safe, et reprogramme le refresh automatique sur la nouvelle
        échéance."""
        logger.info("401 received: token rejected, forcing a refresh.")
        token_data = self._refresh_token()
        with self._token_lock:
            self.token_data = token_data
            self.token = token_data.get("access_token")
            self.refresh_interval = _seconds_left(token_data)
        self._start_background_refresh()

    # -- Requêtes de base ---------------------------------------------------

    @staticmethod
    def _send(send, url: str, **kwargs: Any) -> requests.Response:
        """Appelle `send` (une méthode de la session) et convertit les
        erreurs réseau de `requests` en exceptions de la lib."""
        try:
            return send(url, **kwargs)
        except requests.exceptions.Timeout as e:
            raise RequestTimeoutError(
                f"No response from the API after {kwargs.get('timeout', DEFAULT_TIMEOUT)} s", url=url
            ) from e
        except requests.exceptions.ConnectionError as e:
            raise ConnectionFailedError(
                "Cannot reach the API (server unreachable, no connection or SSL error)", url=url
            ) from e
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"The request could not be completed ({type(e).__name__})", url=url) from e

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
        _retry: bool = True,
    ) -> Any:
        url = f"{self.base_url}{endpoint}"
        send = getattr(self._session, method.lower())
        kwargs: dict[str, Any] = {"headers": self._auth_headers(), "timeout": DEFAULT_TIMEOUT}
        if method == "GET":
            kwargs["params"] = params
        else:
            kwargs["json"] = data
        with self._progress(f"{method} {endpoint}"):
            response = self._send(send, url, **kwargs)
        if response.status_code == 401 and _retry:
            self._handle_unauthorized()
            return self._request(method, endpoint, params, data, _retry=False)
        return self._handle_response(response)

    def _get(self, endpoint: str, params: Optional[dict[str, Any]] = None) -> Any:
        return self._request("GET", endpoint, params=params)

    def _post(self, endpoint: str, data: dict[str, Any]) -> Any:
        return self._request("POST", endpoint, data=data)

    def _put(self, endpoint: str, data: dict[str, Any]) -> Any:
        return self._request("PUT", endpoint, data=data)

    def _delete(self, endpoint: str, data: Optional[dict[str, Any]] = None) -> Any:
        return self._request("DELETE", endpoint, data=data)


def _default_token_file(client_id: Optional[str]) -> str:
    """Emplacement par défaut du fichier de token : le dossier cache de
    l'utilisateur, indépendant du dossier courant et hors de tout dépôt git.

    - Windows : %LOCALAPPDATA%/voltalib/
    - Linux / macOS : $XDG_CACHE_HOME/voltalib/ (par défaut ~/.cache/voltalib/)

    Le nom dépend de l'ID client : deux clés API différentes n'écrasent
    jamais le jeton l'une de l'autre.
    """
    if os.name == "nt":
        base = os.getenv("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
    else:
        base = os.getenv("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    key = hashlib.sha256((client_id or "").encode()).hexdigest()[:16]
    return os.path.join(base, "voltalib", f"token-{key}.json")


def _is_valid_token_data(token_data: Any) -> bool:
    """Un jeton exploitable : un dict avec un `access_token` non vide, et
    `expires_in` / `expires_at` convertibles en nombre (s'ils sont présents)."""
    if not isinstance(token_data, dict) or not token_data.get("access_token"):
        return False
    try:
        int(token_data.get("expires_in", 3600))
        float(token_data.get("expires_at", 0))
    except (TypeError, ValueError):
        return False
    return True


def _seconds_left(token_data: dict[str, Any]) -> int:
    """Secondes avant l'expiration du jeton : calculées depuis `expires_at`
    (horodatage Unix) quand il est connu, sinon `expires_in` tel quel."""
    if "expires_at" in token_data:
        return max(int(float(token_data["expires_at"]) - time.time()), 0)
    return int(token_data.get("expires_in", 3600))

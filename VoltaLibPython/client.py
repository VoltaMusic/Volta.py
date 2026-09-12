from __future__ import annotations

import contextlib
import json
import logging
import os
import threading
import time
from typing import Any, Optional

import requests
from dotenv import load_dotenv

from .exceptions import (
    APIError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    ServerError,
)
from .session import _build_session, DEFAULT_TIMEOUT, TOKEN_REFRESH_MARGIN
from .progress import _Spinner
from .endpoints.verbs import Get, Post, Put, Delete

load_dotenv()

logger = logging.getLogger(__name__)


class VoltaClient:
    def __init__(
        self,
        base_url: str = "https://api.volta-music.com",
        token_file: str = "config/token.json",
        show_progress: bool = True,
    ) -> None:
        self.token_file = token_file
        self.base_url = base_url
        self.client_id = os.getenv("CLIENT_ID")
        self.client_secret = os.getenv("CLIENT_SECRET")
        self.show_progress = show_progress

        self._session = _build_session()
        self._token_lock = threading.Lock()
        self._refresh_timer: Optional[threading.Timer] = None
        self._closed = False

        self.token_data: dict[str, Any] = self._load_token()
        self.token: Optional[str] = self.token_data.get("access_token")
        self.refresh_interval: int = int(self.token_data.get("expires_in", 3600))

        self._start_background_refresh()

        self.get = Get(self)
        self.post = Post(self)
        self.put = Put(self)
        self.delete = Delete(self)

    # -- Gestion du token -------------------------------------------------

    def _refresh_token(self) -> dict[str, Any]:
        url = f"{self.base_url}/api/v1/oauth/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        response = self._session.post(url, data=payload, timeout=DEFAULT_TIMEOUT)
        if response.status_code != 200:
            raise APIError(
                f"Failed to refresh token: {response.status_code} - {response.text}"
            )
        token_data = response.json()
        self._save_token(token_data)
        return token_data

    def _save_token(self, token_data: dict[str, Any]) -> None:
        directory = os.path.dirname(self.token_file)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.token_file, "w") as f:
            json.dump(token_data, f, indent=4)

    def _load_token(self) -> dict[str, Any]:
        if os.path.exists(self.token_file):
            with open(self.token_file, "r") as f:
                return json.load(f)
        return self._refresh_token()

    def _start_background_refresh(self) -> None:
        if self._refresh_timer is not None:
            self._refresh_timer.cancel()
        delay = max(self.refresh_interval - TOKEN_REFRESH_MARGIN, 1)
        self._expiry_deadline = time.monotonic() + self.refresh_interval
        self._refresh_timer = threading.Timer(delay, self._background_refresh_tick)
        self._refresh_timer.daemon = True
        self._refresh_timer.start()

    def _remaining_seconds(self) -> int:
        """Temps restant (en secondes) avant l'expiration réelle du token,
        calculé à partir d'une horloge monotone (insensible aux changements
        d'heure système)."""
        return max(int(self._expiry_deadline - time.monotonic()), 0)

    def _save_remaining_time(self) -> None:
        """Met à jour `expires_in` dans le fichier de token avec le temps
        restant réel, plutôt que la valeur d'origine renvoyée par l'API.
        Appelé à l'arrêt du thread de fond (fin de programme, sortie du
        context manager, ou arrêt manuel)."""
        try:
            with self._token_lock:
                remaining = self._remaining_seconds()
                self.token_data["expires_in"] = remaining
                token_data_copy = dict(self.token_data)
            self._save_token(token_data_copy)
        except Exception:
            logger.exception("Impossible de sauvegarder le temps restant du token")

    def _background_refresh_tick(self) -> None:
        try:
            token_data = self._refresh_token()
            with self._token_lock:
                self.token_data = token_data
                self.token = token_data.get("access_token")
                self.refresh_interval = int(token_data.get("expires_in", 3600))
        except Exception:
            logger.exception("Token refresh failed; retrying in 30s")
            self.refresh_interval = 30
        if not self._closed:
            self._start_background_refresh()

    def stop_background_refresh(self) -> None:
        if self._closed:
            return  # déjà arrêté (évite une double sauvegarde via atexit + __exit__)
        self._closed = True
        if self._refresh_timer is not None:
            self._refresh_timer.cancel()
            self._refresh_timer = None
        self._save_remaining_time()

    def __enter__(self) -> "VoltaClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.stop_background_refresh()
        self._session.close()

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

        error_msg = f"API request failed [{response.status_code}] sur {response.url} - {response.text}"

        if response.status_code == 401:
            raise AuthenticationError(error_msg, status_code=401, response_text=response.text)
        elif response.status_code == 404:
            raise NotFoundError(error_msg, status_code=404, response_text=response.text)
        elif response.status_code == 429:
            raise RateLimitError(error_msg, status_code=429, response_text=response.text)
        elif 500 <= response.status_code < 600:
            raise ServerError(error_msg, status_code=response.status_code, response_text=response.text)
        else:
            raise APIError(error_msg, status_code=response.status_code, response_text=response.text)

    def _handle_unauthorized(self) -> None:
        """Force un nouveau jeton suite à un 401 (jeton invalide/expiré côté
        serveur avant même notre propre échéance de refresh), de façon
        thread-safe, et reprogramme le refresh automatique sur la nouvelle
        échéance."""
        logger.info("401 reçu : jeton invalide, rafraîchissement forcé.")
        token_data = self._refresh_token()
        with self._token_lock:
            self.token_data = token_data
            self.token = token_data.get("access_token")
            self.refresh_interval = int(token_data.get("expires_in", 3600))
        self._start_background_refresh()

    # -- Requêtes de base ---------------------------------------------------

    def _get(
        self, endpoint: str, params: Optional[dict[str, Any]] = None, _retry: bool = True
    ) -> Any:
        url = f"{self.base_url}{endpoint}"
        with self._progress(f"GET {endpoint}"):
            response = self._session.get(
                url, headers=self._auth_headers(), params=params, timeout=DEFAULT_TIMEOUT
            )
        if response.status_code == 401 and _retry:
            self._handle_unauthorized()
            return self._get(endpoint, params, _retry=False)
        return self._handle_response(response)

    def _post(
        self, endpoint: str, data: dict[str, Any], _retry: bool = True
    ) -> Any:
        url = f"{self.base_url}{endpoint}"
        with self._progress(f"POST {endpoint}"):
            response = self._session.post(
                url, headers=self._auth_headers(), json=data, timeout=DEFAULT_TIMEOUT
            )
        if response.status_code == 401 and _retry:
            self._handle_unauthorized()
            return self._post(endpoint, data, _retry=False)
        return self._handle_response(response)

    def _put(
        self, endpoint: str, data: dict[str, Any], _retry: bool = True
    ) -> Any:
        url = f"{self.base_url}{endpoint}"
        with self._progress(f"PUT {endpoint}"):
            response = self._session.put(
                url, headers=self._auth_headers(), json=data, timeout=DEFAULT_TIMEOUT
            )
        if response.status_code == 401 and _retry:
            self._handle_unauthorized()
            return self._put(endpoint, data, _retry=False)
        return self._handle_response(response)

    def _delete(
        self, endpoint: str, data: Optional[dict[str, Any]] = None, _retry: bool = True,
    ) -> Any:
        url = f"{self.base_url}{endpoint}"
        with self._progress(f"DELETE {endpoint}"):
            response = self._session.delete(
                url, headers=self._auth_headers(), json=data, timeout=DEFAULT_TIMEOUT
            )
        if response.status_code == 401 and _retry:
            self._handle_unauthorized()
            return self._delete(endpoint, data, _retry=False)
        return self._handle_response(response)

from __future__ import annotations

import atexit
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
    ConfigurationError,
    ConnectionFailedError,
    InvalidResponseError,
    NetworkError,
    RequestTimeoutError,
    TokenStorageError,
    error_from_response,
)
from .session import (
    _build_session,
    _mount_token_retry,
    DEFAULT_TIMEOUT,
    TOKEN_ENDPOINT,
    TOKEN_REFRESH_MARGIN,
)
from .progress import _Spinner
from .endpoints.verbs import Get, Post, Put, Delete

logger = logging.getLogger(__name__)


class VoltaClient:
    def __init__(
        self,
        base_url: str = "https://api.volta-music.com",
        token_file: str = "config/token.json",
        show_progress: bool = False,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ) -> None:
        self.token_file = token_file
        self.base_url = base_url
        # Les identifiants passés en argument priment sur l'environnement.
        # Le .env n'est lu qu'ici, et seulement s'il manque quelque chose :
        # importer la lib ne modifie jamais os.environ.
        if not (client_id and client_secret):
            load_dotenv()
        self.client_id = client_id or os.getenv("CLIENT_ID")
        self.client_secret = client_secret or os.getenv("CLIENT_SECRET")
        self.show_progress = show_progress

        self._session = _build_session()
        _mount_token_retry(self._session, self.base_url)
        self._token_lock = threading.Lock()
        self._refresh_timer: Optional[threading.Timer] = None
        self._closed = False

        self.token_data: dict[str, Any] = self._load_token()
        self.token: Optional[str] = self.token_data.get("access_token")
        self.refresh_interval: int = int(self.token_data.get("expires_in", 3600))

        self._start_background_refresh()
        # Filet de sécurité si le client n'est ni utilisé avec `with` ni
        # fermé à la main : le temps restant du token est quand même
        # sauvegardé à la fin du programme.
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
                f"{' et '.join(missing)} manquant(s). Passe-les à VoltaClient(client_id=..., client_secret=...) "
                "ou ajoute-les dans le fichier .env à la racine du projet "
                "(et vérifie qu'une variable d'environnement vide du même nom ne les masque pas)."
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
                response.status_code, response.text, "Échec du rafraîchissement du token",
                headers=getattr(response, "headers", None),
            )
        try:
            token_data = response.json()
        except ValueError as e:
            raise InvalidResponseError(
                "Échec du rafraîchissement du token : la réponse de l'API n'est pas du JSON",
                response_text=response.text,
            ) from e
        if not _is_valid_token_data(token_data):
            raise InvalidResponseError(
                "Échec du rafraîchissement du token : `access_token` ou `expires_in` absent ou invalide",
                response_text=response.text,
            )
        self._save_token(token_data)
        return token_data

    def _save_token(self, token_data: dict[str, Any]) -> None:
        try:
            directory = os.path.dirname(self.token_file)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(self.token_file, "w") as f:
                json.dump(token_data, f, indent=4)
        except OSError as e:
            raise TokenStorageError(
                f"Impossible d'écrire le fichier de token ({e.strerror or e})", path=self.token_file
            ) from e

    def _load_token(self) -> dict[str, Any]:
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, "r") as f:
                    token_data = json.load(f)
            except OSError as e:
                raise TokenStorageError(
                    f"Impossible de lire le fichier de token ({e.strerror or e})", path=self.token_file
                ) from e
            except ValueError:
                token_data = None
            if _is_valid_token_data(token_data):
                return token_data
            # Fichier corrompu ou incomplet : pas une raison de planter, on
            # redemande simplement un jeton (qui réécrira le fichier).
            logger.warning("Fichier de token invalide (%s), un nouveau jeton va être demandé.", self.token_file)
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
            return  # déjà arrêté (évite une double sauvegarde, ex. close() puis __exit__)
        self._closed = True
        if self._refresh_timer is not None:
            self._refresh_timer.cancel()
            self._refresh_timer = None
        self._save_remaining_time()

    def close(self) -> None:
        """Arrête le rafraîchissement automatique, sauvegarde le temps
        restant du token et ferme la session HTTP. Peut être appelée
        plusieurs fois sans effet de bord."""
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
            response.status_code, response.text, f"Requête vers {response.url} échouée",
            headers=getattr(response, "headers", None),
        )

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

    @staticmethod
    def _send(send, url: str, **kwargs: Any) -> requests.Response:
        """Appelle `send` (une méthode de la session) et convertit les
        erreurs réseau de `requests` en exceptions de la lib."""
        try:
            return send(url, **kwargs)
        except requests.exceptions.Timeout as e:
            raise RequestTimeoutError(
                f"Pas de réponse de l'API après {kwargs.get('timeout', DEFAULT_TIMEOUT)} s", url=url
            ) from e
        except requests.exceptions.ConnectionError as e:
            raise ConnectionFailedError(
                "Impossible de joindre l'API (serveur injoignable, pas de connexion ou erreur SSL)", url=url
            ) from e
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"La requête n'a pas pu aboutir ({type(e).__name__})", url=url) from e

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


def _is_valid_token_data(token_data: Any) -> bool:
    """Un jeton exploitable : un dict avec un `access_token` non vide et un
    `expires_in` convertible en entier (s'il est présent)."""
    if not isinstance(token_data, dict) or not token_data.get("access_token"):
        return False
    try:
        int(token_data.get("expires_in", 3600))
    except (TypeError, ValueError):
        return False
    return True

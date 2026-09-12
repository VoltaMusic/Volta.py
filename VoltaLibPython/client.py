from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv

from .exceptions import (
    APIError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    ServerError,
)

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 20
TOKEN_REFRESH_MARGIN = 30


def _build_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=(500, 502, 503, 504),
        allowed_methods=("GET", "POST"),
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


class VoltaClient:
    def __init__(
        self,
        base_url: str = "https://api.volta-music.com",
        token_file: str = "config/token.json",
    ) -> None:
        self.token_file = token_file
        self.base_url = base_url
        self.client_id = os.getenv("CLIENT_ID")
        self.client_secret = os.getenv("CLIENT_SECRET")

        self._session = _build_session()
        self._token_lock = threading.Lock()
        self._refresh_timer: Optional[threading.Timer] = None
        self._closed = False

        self.token_data: dict[str, Any] = self._load_token()
        self.token: Optional[str] = self.token_data.get("access_token")
        self.refresh_interval: int = int(self.token_data.get("expires_in", 3600))

        self._start_background_refresh()

        # Sous-espaces de l'API, liés à cette instance (pas de nouveau
        # VoltaClient créé à chaque accès).
        self.get = self._GET(self)
        self.post = self._POST(self)
        self.put = self._PUT(self)
        self.delete = self._DELETE(self)

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

    # -- Rafraîchissement suite à un 401 ------------------------------------

    def _handle_response(self, response: requests.Response) -> Any:
        """
        Analyse la réponse HTTP et lève l'exception spécifique adaptée.
        """
        if response.status_code == 200:
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
        response = self._session.delete(
            url, headers=self._auth_headers(), json=data, timeout=DEFAULT_TIMEOUT
        )
        if response.status_code == 401 and _retry:
            self._handle_unauthorized()
            return self._delete(endpoint, data, _retry=False)
        return self._handle_response(response) 


    # -- Sous-espaces ---------------------------------------------------

    class _GET:
        def __init__(self, client: "VoltaClient") -> None:
            self.client = client
            self.library = VoltaClient._Library(client)
            self.catalog = VoltaClient._Catalog(client)

        def request(self, endpoint: str) -> Any:
            return self.client._get(endpoint)
    class _POST:
        def __init__(self, client: "VoltaClient") -> None:
            self.client = client

        def request(self, endpoint: str, data: dict[str, Any]) -> Any:
            return self.client._post(endpoint, data)

        def track(self, data: dict[str, Any]) -> Any:
            return self.client._post("/api/v1/library/tracks", data)
    class _PUT:
        def __init__(self, client: "VoltaClient") -> None:
            self.client = client

        def request(self, endpoint: str, data: dict[str, Any]) -> Any:
            return self.client._put(endpoint, data)
    class _DELETE:
        def __init__(self, client: "VoltaClient") -> None:
            self.client = client

        def request(self, endpoint: str, data: dict[str, Any]) -> Any:
            return self.client._delete(endpoint, data)

        def track(self, track_id: str) -> Any:
            return self.client._delete(f"/api/v1/library/tracks/{track_id}")

    # -- Sous-espaces de l'API liés à VoltaClient -----------------------------

    class _Library:
        def __init__(self, client: "VoltaClient") -> None:
            self.client = client
            self.endpoint = "/api/v1/library"
        def tracks(self, search: str = None) -> Any:
            """
            Get all liked tracks.

            If a search string is provided, filter the tracks by title containing the search string (case-insensitive).

            Args:
                search (str, optional): A string to filter tracks by title. Defaults to None.
            """
            result = self.client._get(f"{self.endpoint}/tracks")
            if search:
                track = []
                if isinstance(result, list):
                    query_lower = search.lower()
                    for item in result:
                        if isinstance(item, dict) and query_lower in item.get("title", "").lower():
                            track.append(item)
                return track
            return result
        def albums(self, search: str = None) -> Any:
            """
            Get all liked albums.

            If a search string is provided, filter the albums by title containing the search string (case-insensitive).

            Args:
                search (str, optional): A string to filter albums by title. Defaults to None.
            """
            result = self.client._get(f"{self.endpoint}/albums")
            if search:
                album = []
                if isinstance(result, list):
                    query_lower = search.lower()
                    for item in result:
                        if isinstance(item, dict) and query_lower in item.get("title", "").lower():
                            album.append(item)
                return album
            return result
        def artists(self, search: str = None) -> Any:
            """
            Get all liked artists.

            If a search string is provided, filter the artists by name containing the search string (case-insensitive).

            Args:
                search (str, optional): A string to filter artists by name. Defaults to None.
            """
            result = self.client._get(f"{self.endpoint}/artists")
            if search:
                artist = []
                if isinstance(result, list):
                    query_lower = search.lower()
                    for item in result:
                        if isinstance(item, dict) and query_lower in item.get("name", "").lower():
                            artist.append(item)
                return artist
            return result
        def artist_albums(self, id: str) -> Any:
            """
            Get all albums of a specific artist by their ID.

            Args:
                id (str): The ID of the artist.
            """
            return self.client._get(f"{self.endpoint}/artists/{id}/albums")
        def artist_tracks(self, id: str) -> Any:
            """
            Get all tracks of a specific artist by their ID.

            Args:
                id (str): The ID of the artist.
            """
            return self.client._get(f"{self.endpoint}/artists/{id}/tracks")
        def playlists(self, search: str = None, id: str = None) -> Any:
            """
            Get all liked playlists or a specific playlist by ID.

            If a search string is provided, filter the playlists by name containing the search string (case-insensitive).
            If both search and id are provided, a ValueError will be raised.

            Args:
                search (str, optional): A string to filter playlists by name. Defaults to None.
                    search is just for finding playlists by name, while id is for fetching a specific playlist.
                id (str, optional): The ID of a specific playlist. Defaults to None.
                    id is for fetching all data and tracks of a specific playlist, while search is just for finding playlists by name.
            """
            if search is not None and id is not None:
                raise ValueError("search and id cannot be used at the same time")
            if id:
                return self.client._get(f"{self.endpoint}/playlists/{id}")
            result = self.client._get(f"{self.endpoint}/playlists")
            if search:
                playlist = []
                if isinstance(result, list):
                    query_lower = search.lower()
                    for item in result:
                        if isinstance(item, dict) and query_lower in item.get("name", "").lower():
                            playlist.append(item)
                return playlist
            return result

    class _Catalog:
        def __init__(self, client: "VoltaClient") -> None:
            self.client = client
            self.endpoint = "/api/v1"
        def search(self, query: str) -> Any:
            """
            Search for tracks, albums, artists, and playlists globally.

            Args:
                query (str): The search query string.
            """
            return self.client._get(f"{self.endpoint}/search?q={query}")
        def artist(self, id: str) -> Any:
            """
            Get details of a specific artist by their ID.
            Get famous tracks, all albums, and all related information.

            Args:
                id (str): The ID of the artist.
            """
            return self.client._get(f"{self.endpoint}/artists/{id}")
        def album(self, id: str) -> Any:
            """
            Get details of a specific album by its ID.
            Get all tracks of the album.

            Args:
                id (str): The ID of the album.
            """
            return self.client._get(f"{self.endpoint}/album/{id}")
        def track(self, id: str) -> Any:
            """
            Get metadata of a specific track by its ID.

            Args:
                id (str): The ID of the track.
            """
            return self.client._get(f"{self.endpoint}/track/{id}")
        def playlist(self, id: str) -> Any:
            """
            Get details of a specific playlist by its ID.
            Get all tracks of the playlist.

            Args:
                id (str): The ID of the playlist.
            """
            #return self.client._get(f"{self.endpoint}/playlist/{id}")
            raise NotImplementedError("catalog.playlist() is not implemented yet because the upstream playlist endpoint is currently not working")
        def home(self) -> Any:
            """
            Get the home page data, including recommended tracks, albums, artists, and playlists.
            """
            return self.client._get(f"{self.endpoint}/home")

        # GET /api/v1/stream?track_id=… stream:read

        def state(self) -> Any:
            """
            Get the current playback state (endpoint: /playback/state).
            """
            return self.client._get(f"{self.endpoint}/playback/state")
        def me(self) -> Any:
            """
            Get the current user's profile information, including username, email, and subscription status.
            """
            return self.client._get(f"{self.endpoint}/auth/me")

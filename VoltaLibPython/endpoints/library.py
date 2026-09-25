from __future__ import annotations

import unicodedata
from typing import Any, Optional

from ..exceptions import InvalidArgumentError, InvalidResponseError
from ._base import _Endpoint


def _normalize(text: str) -> str:
    """Forme de comparaison : insensible à la casse et aux accents
    ("Beyoncé" et "beyonce" donnent la même chose)."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _filter(result: Any, key: str, search: str) -> list[Any]:
    """Garde les éléments de `result` dont le champ `key` contient `search`.

    Lève InvalidResponseError si l'API n'a pas renvoyé une liste : filtrer
    une autre forme de réponse n'a pas de sens, et renvoyer une liste vide
    ferait croire à tort qu'il n'y a aucun résultat. Les éléments qui ne
    sont pas des dicts, ou dont le champ est absent / null, sont ignorés.
    """
    if not isinstance(result, list):
        raise InvalidResponseError(
            f"Cannot search: the API should have returned a list, it returned {type(result).__name__}",
            response_text=str(result),
        )
    query = _normalize(search)
    return [
        item for item in result
        if isinstance(item, dict) and isinstance(item.get(key), str) and query in _normalize(item[key])
    ]


class Library(_Endpoint):
    endpoint = "/api/v1/library"

    def tracks(self, search: Optional[str] = None) -> Any:
        """
        Get all liked tracks.

        If a search string is provided, filter the tracks by title containing the search string (case- and accent-insensitive).
        Raises InvalidResponseError if the API doesn't return a list.

        Args:
            search (str, optional): A string to filter tracks by title. Defaults to None.
        """
        result = self.client._get(self._path("tracks"))
        if search:
            return _filter(result, "title", search)
        return result
    def albums(self, search: Optional[str] = None) -> Any:
        """
        Get all liked albums.

        If a search string is provided, filter the albums by title containing the search string (case- and accent-insensitive).
        Raises InvalidResponseError if the API doesn't return a list.

        Args:
            search (str, optional): A string to filter albums by title. Defaults to None.
        """
        result = self.client._get(self._path("albums"))
        if search:
            return _filter(result, "title", search)
        return result
    def artists(self, search: Optional[str] = None) -> Any:
        """
        Get all liked artists.

        If a search string is provided, filter the artists by name containing the search string (case- and accent-insensitive).
        Raises InvalidResponseError if the API doesn't return a list.

        Args:
            search (str, optional): A string to filter artists by name. Defaults to None.
        """
        result = self.client._get(self._path("artists"))
        if search:
            return _filter(result, "name", search)
        return result
    def artist_albums(self, id: str) -> Any:
        """
        Get all albums of a specific artist by their ID.

        Args:
            id (str): The ID of the artist.
        """
        return self.client._get(self._path("artists", id, "albums"))
    def artist_tracks(self, id: str) -> Any:
        """
        Get all tracks of a specific artist by their ID.

        Args:
            id (str): The ID of the artist.
        """
        return self.client._get(self._path("artists", id, "tracks"))
    def playlists(self, search: Optional[str] = None, id: Optional[str] = None) -> Any:
        """
        Get all liked playlists or a specific playlist by ID.

        If a search string is provided, filter the playlists by name containing the search string (case- and accent-insensitive).
        Raises InvalidResponseError if the API doesn't return a list.
        If both search and id are provided, an InvalidArgumentError will be raised.

        Args:
            search (str, optional): A string to filter playlists by name. Defaults to None.
                search is just for finding playlists by name, while id is for fetching a specific playlist.
            id (str, optional): The ID of a specific playlist. Defaults to None.
                id is for fetching all data and tracks of a specific playlist, while search is just for finding playlists by name.
        """
        if search is not None and id is not None:
            raise InvalidArgumentError("`search` and `id` can't be used together")
        if id:
            return self.client._get(self._path("playlists", id))
        result = self.client._get(self._path("playlists"))
        if search:
            return _filter(result, "name", search)
        return result

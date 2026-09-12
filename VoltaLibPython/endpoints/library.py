from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import VoltaClient


class Library:
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

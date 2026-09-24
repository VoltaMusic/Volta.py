from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ._url import segment

if TYPE_CHECKING:
    from ..client import VoltaClient


class Catalog:
    def __init__(self, client: "VoltaClient") -> None:
        self.client = client
        self.endpoint = "/api/v1"
    def search(self, query: str) -> Any:
        """
        Search for tracks, albums, artists, and playlists globally.

        Args:
            query (str): The search query string.
        """
        return self.client._get(f"{self.endpoint}/search", params={"q": query})
    def artist(self, id: str) -> Any:
        """
        Get details of a specific artist by their ID.
        Get famous tracks, all albums, and all related information.

        Args:
            id (str): The ID of the artist.
        """
        return self.client._get(f"{self.endpoint}/artists/{segment(id)}")
    def album(self, id: str) -> Any:
        """
        Get details of a specific album by its ID.
        Get all tracks of the album.

        Args:
            id (str): The ID of the album.
        """
        return self.client._get(f"{self.endpoint}/album/{segment(id)}")
    def track(self, id: str) -> Any:
        """
        Get metadata of a specific track by its ID.

        Args:
            id (str): The ID of the track.
        """
        return self.client._get(f"{self.endpoint}/track/{segment(id)}")
    def playlist(self, id: str) -> Any:
        """
        Get details of a specific playlist by its ID.
        Get all tracks of the playlist.

        Args:
            id (str): The ID of the playlist.
        """
        return self.client._get(f"{self.endpoint}/playlist/{segment(id)}")
    def home(self) -> Any:
        """
        Get the home page data, including recommended tracks, albums, artists, and playlists.
        """
        return self.client._get(f"{self.endpoint}/home")
    def stream(self, id:str) -> Any:
        """
        Get info of the song andthe streaming url
        (Streaming url: /api/v1/stream_relay_ref?ref=volta_relay_ref_xxxxxxxxxxxxxxxx).

        Args:
            id (str): The ID of the track.
        """
        return self.client._get(f"{self.endpoint}/stream", params={"track_id": id})
    def state(self) -> Any:
        """
        Get the current playback state (endpoint: /playback/state).
        """
        return self.client._get(f"{self.endpoint}/playback/state")
    def me(self) -> Any:
        """
        Get the current user's public profile: `sub` (user ID), `name`,
        `preferred_username`, `nickname` and `picture` (avatar URL).
        The email address is never returned.

        Scope: profile:read
        """
        return self.client._get(f"{self.endpoint}/auth/me")

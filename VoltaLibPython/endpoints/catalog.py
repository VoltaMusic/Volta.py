from __future__ import annotations

from typing import Any, TYPE_CHECKING

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
        # return self.client._get(f"{self.endpoint}/playlist/{id}")
        raise NotImplementedError(
            "catalog.playlist() is not implemented yet because the upstream playlist endpoint is currently not working"
        )

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

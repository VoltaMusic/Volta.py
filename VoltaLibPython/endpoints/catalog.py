from __future__ import annotations

from typing import Any

from ._base import _Endpoint


class Catalog(_Endpoint):
    endpoint = "/api/v1"

    def search(self, query: str) -> Any:
        """
        Search for tracks, albums, artists, and playlists globally.

        Args:
            query (str): The search query string.
        """
        return self.client._get(self._path("search"), params={"q": query})
    def artist(self, id: str) -> Any:
        """
        Get details of a specific artist by their ID.
        Get famous tracks, all albums, and all related information.

        Args:
            id (str): The ID of the artist.
        """
        return self.client._get(self._path("artists", id))
    def album(self, id: str) -> Any:
        """
        Get details of a specific album by its ID.
        Get all tracks of the album.

        Args:
            id (str): The ID of the album.
        """
        return self.client._get(self._path("album", id))
    def track(self, id: str) -> Any:
        """
        Get metadata of a specific track by its ID.

        Args:
            id (str): The ID of the track.
        """
        return self.client._get(self._path("track", id))
    def playlist(self, id: str) -> Any:
        """
        Get details of a specific playlist by its ID.
        Get all tracks of the playlist.

        Args:
            id (str): The ID of the playlist.
        """
        return self.client._get(self._path("playlist", id))
    def home(self) -> Any:
        """
        Get the home page data, including recommended tracks, albums, artists, and playlists.
        """
        return self.client._get(self._path("home"))
    def stream(self, id:str) -> Any:
        """
        Get info of the song andthe streaming url
        (Streaming url: /api/v1/stream_relay_ref?ref=volta_relay_ref_xxxxxxxxxxxxxxxx).

        Args:
            id (str): The ID of the track.
        """
        return self.client._get(self._path("stream"), params={"track_id": id})
    def state(self) -> Any:
        """
        Get the current playback state (endpoint: /playback/state).
        """
        return self.client._get(self._path("playback", "state"))
    def me(self) -> Any:
        """
        Get the current user's public profile: `sub` (user ID), `name`,
        `preferred_username`, `nickname` and `picture` (avatar URL).
        The email address is never returned.

        Scope: profile:read
        """
        return self.client._get(self._path("auth", "me"))

from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import VoltaClient


def _playlist_fields(
    name: Optional[str], description: Optional[str], is_public: Optional[bool]
) -> dict[str, Any]:
    """Only keep the fields that were actually given, so an update never
    overwrites a field the caller didn't mean to touch."""
    fields = {"name": name, "description": description, "is_public": is_public}
    return {key: value for key, value in fields.items() if value is not None}


class LibraryPost:
    def __init__(self, client: "VoltaClient") -> None:
        self.client = client
        self.endpoint = "/api/v1/library"
    def track(self, track_id: str) -> Any:
        """
        Add a track to your library (like it).

        Scope: library:write

        Args:
            track_id (str): The ID of the track.
        """
        return self.client._post(f"{self.endpoint}/tracks", {"track_id": track_id})
    def playlist(self, name: str, description: Optional[str] = None, is_public: Optional[bool] = None) -> Any:
        """
        Create a new playlist.

        Scope: playlists:write

        Args:
            name (str): The name of the playlist.
            description (str, optional): The description of the playlist. Defaults to None.
            is_public (bool, optional): Whether the playlist is public. Defaults to None (server default).
        """
        if not name:
            raise ValueError("name is required to create a playlist")
        return self.client._post(f"{self.endpoint}/playlists", _playlist_fields(name, description, is_public))
    def playlist_track(self, playlist_id: str, track_id: str) -> Any:
        """
        Add a track to a playlist.

        Scope: playlists:write

        Args:
            playlist_id (str): The ID of the playlist.
            track_id (str): The ID of the track to add.
        """
        return self.client._post(f"{self.endpoint}/playlists/{playlist_id}/tracks", {"track_id": track_id})


class LibraryPut:
    def __init__(self, client: "VoltaClient") -> None:
        self.client = client
        self.endpoint = "/api/v1/library"
    def playlist(
        self,
        playlist_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_public: Optional[bool] = None,
    ) -> Any:
        """
        Update the name, description and/or visibility of a playlist.

        Only the fields you pass are sent; the others are left unchanged.
        Raises a ValueError if no field is given.

        Scope: playlists:write

        Args:
            playlist_id (str): The ID of the playlist.
            name (str, optional): The new name. Defaults to None (unchanged).
            description (str, optional): The new description. Defaults to None (unchanged).
            is_public (bool, optional): The new visibility. Defaults to None (unchanged).
        """
        fields = _playlist_fields(name, description, is_public)
        if not fields:
            raise ValueError("at least one of name, description or is_public must be given")
        return self.client._put(f"{self.endpoint}/playlists/{playlist_id}", fields)
    def reorder(self, playlist_id: str, track_ids: list[str]) -> Any:
        """
        Reorder the tracks of a playlist.

        Scope: playlists:write

        Args:
            playlist_id (str): The ID of the playlist.
            track_ids (list[str]): The track IDs of the playlist, in the new order.
        """
        return self.client._put(
            f"{self.endpoint}/playlists/{playlist_id}/tracks/reorder", {"track_ids": list(track_ids)}
        )


class LibraryDelete:
    def __init__(self, client: "VoltaClient") -> None:
        self.client = client
        self.endpoint = "/api/v1/library"
    def track(self, track_id: str) -> Any:
        """
        Remove a track from your library.

        Scope: library:write

        Args:
            track_id (str): The ID of the track.
        """
        return self.client._delete(f"{self.endpoint}/tracks/{track_id}")
    def album(self, album_id: str) -> Any:
        """
        Remove every track of an album from your library.

        Scope: library:write

        Args:
            album_id (str): The ID of the album.
        """
        return self.client._delete(f"{self.endpoint}/albums/{album_id}")
    def artist(self, artist_id: str) -> Any:
        """
        Unfollow an artist.

        Scope: library:write

        Args:
            artist_id (str): The ID of the artist.
        """
        return self.client._delete(f"{self.endpoint}/artists/{artist_id}")
    def playlist(self, playlist_id: str) -> Any:
        """
        Delete a playlist.

        Scope: playlists:write

        Args:
            playlist_id (str): The ID of the playlist.
        """
        return self.client._delete(f"{self.endpoint}/playlists/{playlist_id}")
    def playlist_track(self, playlist_id: str, track_id: str) -> Any:
        """
        Remove a track from a playlist.

        Scope: playlists:write

        Args:
            playlist_id (str): The ID of the playlist.
            track_id (str): The ID of the track to remove.
        """
        return self.client._delete(f"{self.endpoint}/playlists/{playlist_id}/tracks/{track_id}")

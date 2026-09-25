from __future__ import annotations

from typing import Any, Mapping, Optional, TYPE_CHECKING

from ..exceptions import InvalidArgumentError
from ._url import segment

if TYPE_CHECKING:
    from ..client import VoltaClient


def _playlist_fields(
    name: Optional[str], description: Optional[str], is_public: Optional[bool]
) -> dict[str, Any]:
    """Only keep the fields that were actually given, so an update never
    overwrites a field the caller didn't mean to touch."""
    fields = {"name": name, "description": description, "is_public": is_public}
    return {key: value for key, value in fields.items() if value is not None}


def _names(value: Any) -> Optional[str]:
    """"Daft Punk" -> "Daft Punk" ; [{"name": "A"}, {"name": "B"}] -> "A, B" ; {"name": "X"} -> "X"."""
    if isinstance(value, str):
        return value or None
    if isinstance(value, Mapping):
        return _names(value.get("name"))
    if isinstance(value, list):
        names = [n for n in (_names(v) for v in value) if n]
        return ", ".join(names) or None
    return None


def _track_payload(track: Any) -> dict[str, Any]:
    """Construit le corps attendu par l'API pour ajouter un titre, à partir
    d'un titre tel que renvoyé par la lib, quelle que soit sa source :

    - bibliothèque (`get.library.tracks()`) : `title`, `artist` et `album`
      en texte, `artist_id`, `album_id`, `cover_url` ;
    - catalogue (`get.catalog.track()`, `search()`...) : `name`, `artists`
      (liste de {"id", "name"}) et `album` ({"id", "name", "images"}).

    L'API exige `id`, `name`, `artist` et `album` ; les autres champs sont
    envoyés quand ils sont connus.
    """
    if isinstance(track, str):
        raise InvalidArgumentError(
            "pass the whole track (the dict returned by get.library.tracks(), get.catalog.track()...), "
            "not just its ID: the API also needs its name, artist and album"
        )
    if not isinstance(track, Mapping):
        raise InvalidArgumentError(f"invalid track: a dict is expected, not {type(track).__name__}")

    album = track.get("album")
    album_obj = album if isinstance(album, Mapping) else {}
    artists = track.get("artists") if isinstance(track.get("artists"), list) else []
    first_artist = artists[0] if artists and isinstance(artists[0], Mapping) else {}
    images = album_obj.get("images") if isinstance(album_obj.get("images"), list) else []
    first_image = images[0] if images and isinstance(images[0], Mapping) else {}

    payload = {
        "id": track.get("id") or track.get("track_id"),
        "name": track.get("name") or track.get("title"),
        "artist": _names(track.get("artist")) or _names(artists),
        "album": _names(album),
    }
    missing = [key for key, value in payload.items() if not value]
    if missing:
        raise InvalidArgumentError(f"incomplete track, missing field(s): {', '.join(missing)}")
    payload["id"] = str(payload["id"])

    optional = {
        "artist_id": track.get("artist_id") or first_artist.get("id"),
        "album_id": track.get("album_id") or album_obj.get("id"),
        "cover_url": track.get("cover_url") or first_image.get("url"),
        "duration_ms": track.get("duration_ms"),
    }
    payload.update({key: value for key, value in optional.items() if value is not None})
    return payload


class LibraryPost:
    def __init__(self, client: "VoltaClient") -> None:
        self.client = client
        self.endpoint = "/api/v1/library"
    def track(self, track: Mapping[str, Any]) -> Any:
        """
        Add a track to your library (like it).

        The API needs the track's name, artist and album, not just its ID:
        pass the track dict as returned by `get.catalog.track()`,
        `get.catalog.search()` or `get.library.tracks()`.

        Scope: library:write

        Args:
            track (dict): The track to add.
        """
        return self.client._post(f"{self.endpoint}/tracks", _track_payload(track))
    def playlist(self, name: str, description: Optional[str] = None, is_public: Optional[bool] = None) -> Any:
        """
        Create a new playlist.

        Scope: playlists:write

        Args:
            name (str): The name of the playlist.
            description (str, optional): The description of the playlist. Defaults to None.
                The API ignores it on creation, so it is set right after with a PUT.
            is_public (bool, optional): Whether the playlist is public. Defaults to None (server default).
        """
        if not name:
            raise InvalidArgumentError("`name` is required to create a playlist")
        created = self.client._post(f"{self.endpoint}/playlists", _playlist_fields(name, description, is_public))
        # L'API ignore la description à la création (elle revient à null) mais
        # l'accepte en modification : on la pose juste après si besoin.
        if description and isinstance(created, dict) and created.get("id") and created.get("description") != description:
            updated = self.client._put(
                f"{self.endpoint}/playlists/{segment(created['id'])}", {"description": description}
            )
            if isinstance(updated, dict):
                created = {**created, **updated}
        return created
    def playlist_track(self, playlist_id: str, track: Mapping[str, Any]) -> Any:
        """
        Add a track to a playlist.

        The API needs the track's name, artist and album, not just its ID:
        pass the track dict as returned by `get.library.tracks()`,
        `get.catalog.track()` or `get.catalog.search()`.

        Scope: playlists:write

        Args:
            playlist_id (str): The ID of the playlist.
            track (dict): The track to add.
        """
        return self.client._post(
            f"{self.endpoint}/playlists/{segment(playlist_id)}/tracks", _track_payload(track)
        )


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
        Raises an InvalidArgumentError if no field is given.

        Scope: playlists:write

        Args:
            playlist_id (str): The ID of the playlist.
            name (str, optional): The new name. Defaults to None (unchanged).
            description (str, optional): The new description. Defaults to None (unchanged).
            is_public (bool, optional): The new visibility. Defaults to None (unchanged).
        """
        fields = _playlist_fields(name, description, is_public)
        if not fields:
            raise InvalidArgumentError("give at least one field to update: `name`, `description` or `is_public`")
        return self.client._put(f"{self.endpoint}/playlists/{segment(playlist_id)}", fields)
    def reorder(self, playlist_id: str, track_ids: list[str]) -> Any:
        """
        Reorder the tracks of a playlist.

        Scope: playlists:write

        Args:
            playlist_id (str): The ID of the playlist.
            track_ids (list[str]): The track IDs of the playlist, in the new order.
        """
        return self.client._put(
            f"{self.endpoint}/playlists/{segment(playlist_id)}/tracks/reorder", {"track_ids": list(track_ids)}
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
        return self.client._delete(f"{self.endpoint}/tracks/{segment(track_id)}")
    def album(self, album_id: str) -> Any:
        """
        Remove every track of an album from your library.

        Scope: library:write

        Args:
            album_id (str): The ID of the album.
        """
        return self.client._delete(f"{self.endpoint}/albums/{segment(album_id)}")
    def artist(self, artist_id: str) -> Any:
        """
        Unfollow an artist.

        Scope: library:write

        Args:
            artist_id (str): The ID of the artist.
        """
        return self.client._delete(f"{self.endpoint}/artists/{segment(artist_id)}")
    def playlist(self, playlist_id: str) -> Any:
        """
        Delete a playlist.

        Scope: playlists:write

        Args:
            playlist_id (str): The ID of the playlist.
        """
        return self.client._delete(f"{self.endpoint}/playlists/{segment(playlist_id)}")
    def playlist_track(self, playlist_id: str, track_id: str) -> Any:
        """
        Remove a track from a playlist.

        Scope: playlists:write

        Args:
            playlist_id (str): The ID of the playlist.
            track_id (str): The ID of the track to remove.
        """
        return self.client._delete(f"{self.endpoint}/playlists/{segment(playlist_id)}/tracks/{segment(track_id)}")

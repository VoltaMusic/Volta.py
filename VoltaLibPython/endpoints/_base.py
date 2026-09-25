from __future__ import annotations

from typing import TYPE_CHECKING

from ._url import segment

if TYPE_CHECKING:
    from ..client import VoltaClient


class _Endpoint:
    """Base des groupes d'endpoints : garde le client parent et construit
    les chemins d'URL à partir de `endpoint`."""

    endpoint = "/api/v1"

    def __init__(self, client: "VoltaClient") -> None:
        self.client = client

    def _path(self, *parts: object) -> str:
        """`_path("playlists", playlist_id, "tracks")` ->
        "/api/v1/library/playlists/<id encodé>/tracks". Chaque partie est
        encodée comme un seul segment : un ID ne peut jamais changer la
        route appelée."""
        return "/".join([self.endpoint, *(segment(part) for part in parts)])

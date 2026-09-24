from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

from .library import Library
from .catalog import Catalog
from .library_write import LibraryPost, LibraryPut, LibraryDelete

if TYPE_CHECKING:
    from ..client import VoltaClient


class Get:
    """Espace de noms pour les requêtes GET. Utilise le client parent,
    ne crée jamais de nouvelle instance de VoltaClient."""

    def __init__(self, client: "VoltaClient") -> None:
        self.client = client
        self.library = Library(client)
        self.catalog = Catalog(client)

    def request(self, endpoint: str) -> Any:
        return self.client._get(endpoint)


class Post:
    """Espace de noms pour les requêtes POST."""

    def __init__(self, client: "VoltaClient") -> None:
        self.client = client
        self.library = LibraryPost(client)

    def request(self, endpoint: str, data: dict[str, Any]) -> Any:
        return self.client._post(endpoint, data)

    def track(self, data: dict[str, Any]) -> Any:
        """Ancien raccourci, gardé pour compatibilité : préférer `post.library.track(track_id)`."""
        return self.client._post("/api/v1/library/tracks", data)


class Put:
    """Espace de noms pour les requêtes PUT."""

    def __init__(self, client: "VoltaClient") -> None:
        self.client = client
        self.library = LibraryPut(client)

    def request(self, endpoint: str, data: dict[str, Any]) -> Any:
        return self.client._put(endpoint, data)


class Delete:
    """Espace de noms pour les requêtes DELETE."""

    def __init__(self, client: "VoltaClient") -> None:
        self.client = client
        self.library = LibraryDelete(client)

    def request(self, endpoint: str, data: Optional[dict[str, Any]] = None) -> Any:
        return self.client._delete(endpoint, data)

    def track(self, track_id: str) -> Any:
        """Ancien raccourci, gardé pour compatibilité : préférer `delete.library.track(track_id)`."""
        return self.client._delete(f"/api/v1/library/tracks/{track_id}")

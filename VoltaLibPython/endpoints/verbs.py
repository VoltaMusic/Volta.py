from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

from .library import Library
from .catalog import Catalog

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
    def __init__(self, client: "VoltaClient") -> None:
        self.client = client

    def request(self, endpoint: str, data: dict[str, Any]) -> Any:
        return self.client._post(endpoint, data)

    def track(self, data: dict[str, Any]) -> Any:
        return self.client._post("/api/v1/library/tracks", data)


class Put:
    def __init__(self, client: "VoltaClient") -> None:
        self.client = client

    def request(self, endpoint: str, data: dict[str, Any]) -> Any:
        return self.client._put(endpoint, data)


class Delete:
    def __init__(self, client: "VoltaClient") -> None:
        self.client = client

    def request(self, endpoint: str, data: Optional[dict[str, Any]] = None) -> Any:
        return self.client._delete(endpoint, data)

    def track(self, track_id: str) -> Any:
        return self.client._delete(f"/api/v1/library/tracks/{track_id}")

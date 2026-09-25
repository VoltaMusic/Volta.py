from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

from .library import Library
from .catalog import Catalog
from .library_write import LibraryPost, LibraryPut, LibraryDelete

if TYPE_CHECKING:
    from ..client import VoltaClient


class Get:
    """Namespace for GET requests. Uses the parent client, never creates
    a new VoltaClient."""

    def __init__(self, client: "VoltaClient") -> None:
        self.client = client
        self.library = Library(client)
        self.catalog = Catalog(client)

    def request(self, endpoint: str) -> Any:
        return self.client._get(endpoint)


class Post:
    """Namespace for POST requests."""

    def __init__(self, client: "VoltaClient") -> None:
        self.client = client
        self.library = LibraryPost(client)

    def request(self, endpoint: str, data: dict[str, Any]) -> Any:
        return self.client._post(endpoint, data)


class Put:
    """Namespace for PUT requests."""

    def __init__(self, client: "VoltaClient") -> None:
        self.client = client
        self.library = LibraryPut(client)

    def request(self, endpoint: str, data: dict[str, Any]) -> Any:
        return self.client._put(endpoint, data)


class Delete:
    """Namespace for DELETE requests."""

    def __init__(self, client: "VoltaClient") -> None:
        self.client = client
        self.library = LibraryDelete(client)

    def request(self, endpoint: str, data: Optional[dict[str, Any]] = None) -> Any:
        return self.client._delete(endpoint, data)

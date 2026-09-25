"""Every exception the library can raise.

Hierarchy:

    VoltaAPIExceptions                  base of everything the library raises
    ├── ConfigurationError              missing credentials (CLIENT_ID / CLIENT_SECRET)
    ├── InvalidArgumentError            invalid argument, caught before any network call (also a ValueError)
    ├── TokenStorageError               the token file can't be read or written
    ├── NetworkError                    the request got no HTTP response
    │   ├── ConnectionFailedError       server unreachable (DNS, connection refused, SSL...)
    │   └── RequestTimeoutError         no response within the timeout
    ├── InvalidResponseError            unusable 2xx response (invalid JSON, expected field missing)
    └── APIError                        the API answered with an HTTP error code
        ├── BadRequestError             400
        ├── AuthenticationError         401
        ├── ForbiddenError              403 (missing scope)
        ├── NotFoundError               404
        ├── ConflictError               409
        ├── UnprocessableEntityError    422 (request body rejected)
        ├── RateLimitError              429
        └── ServerError                 5xx
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Optional


class VoltaAPIExceptions(Exception):
    """Base class for every error raised by the library."""
    pass

class ConfigurationError(VoltaAPIExceptions):
    """Raised when the local configuration is incomplete (e.g. CLIENT_ID missing)."""
    pass

class InvalidArgumentError(VoltaAPIExceptions, ValueError):
    """Raised when an argument passed to a method is invalid, before any
    network call. Also a ValueError, so code that already caught ValueError
    keeps working."""
    pass

class TokenStorageError(VoltaAPIExceptions):
    """Raised when the token file can't be read or written (permissions,
    full disk, invalid path...)."""
    def __init__(self, message: str, path: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.path = path

    def __str__(self) -> str:
        if self.path:
            return f"{self.message}\n  -> file: {self.path}"
        return self.message

class NetworkError(VoltaAPIExceptions):
    """Raised when the request got no HTTP response."""
    def __init__(self, message: str, url: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.url = url

    def __str__(self) -> str:
        if self.url:
            return f"{self.message}\n  -> {self.url}"
        return self.message

class ConnectionFailedError(NetworkError):
    """Raised when the server can't be reached (DNS, connection refused, SSL...)."""
    pass

class RequestTimeoutError(NetworkError):
    """Raised when the server doesn't answer within the timeout."""
    pass

class InvalidResponseError(VoltaAPIExceptions):
    """Raised when the API answers with a success code but the response is
    unusable (invalid JSON, expected field missing)."""
    def __init__(self, message: str, response_text: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.response_text = response_text

    def __str__(self) -> str:
        if self.response_text:
            excerpt = self.response_text.strip()[:200]
            return f"{self.message}\n  -> response received: {excerpt}"
        return self.message

class APIError(VoltaAPIExceptions):
    """Raised when the API returns an HTTP error code."""
    def __init__(self, message: str, status_code: int | None = None, response_text: str | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_text = response_text

    @property
    def detail(self) -> str | None:
        """Error message returned by the API (the JSON `detail` field), or the raw text."""
        if not self.response_text:
            return None
        try:
            data = json.loads(self.response_text)
        except ValueError:
            return self.response_text.strip() or None
        if isinstance(data, dict):
            for key in ("detail", "message", "error_description", "error"):
                if data.get(key):
                    return _format_detail(data[key])
        return self.response_text.strip() or None

    def __str__(self) -> str:
        text = self.message
        if self.status_code is not None:
            text = f"[{self.status_code}] {text}"
        if self.detail:
            text += f"\n  -> {self.detail}"
        return text

class BadRequestError(APIError):
    """Raised on a 400 error (invalid request / missing parameters)."""
    pass

class AuthenticationError(APIError):
    """Raised on a 401 error (unauthorized / invalid token)."""
    pass

class ForbiddenError(APIError):
    """Raised on a 403 error (access denied, usually a missing scope)."""
    pass

class NotFoundError(APIError):
    """Raised on a 404 error (resource not found)."""
    pass

class ConflictError(APIError):
    """Raised on a 409 error (conflict, e.g. the resource already exists)."""
    pass

class UnprocessableEntityError(APIError):
    """Raised on a 422 error (request body rejected by the API)."""
    pass

class RateLimitError(APIError):
    """Raised on a 429 error (too many requests).

    `retry_after`: seconds to wait before retrying, if the API sent them
    (`Retry-After` header), otherwise None.
    """
    def __init__(self, message: str, status_code: int | None = None, response_text: str | None = None,
                 retry_after: int | None = None):
        super().__init__(message, status_code=status_code, response_text=response_text)
        self.retry_after = retry_after

    def __str__(self) -> str:
        text = super().__str__()
        if self.retry_after is not None:
            text += f"\n  -> retry in {self.retry_after} s"
        return text

class ServerError(APIError):
    """Raised on a server error (500, 502, 503, 504)."""
    pass


def _format_detail(value: Any) -> str:
    """Rend lisible le champ `detail` d'une erreur. Gère le format des
    erreurs de validation (liste de {"loc": [...], "msg": "..."}), qui
    sinon s'afficherait comme une liste Python brute."""
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict) and "msg" in item:
                loc = ".".join(str(p) for p in item.get("loc", []) if p != "body")
                parts.append(f"{loc}: {item['msg']}" if loc else str(item["msg"]))
            else:
                parts.append(str(item))
        return "; ".join(parts)
    return str(value)


def _parse_retry_after(headers: Optional[Mapping[str, str]]) -> int | None:
    if not headers:
        return None
    value = headers.get("Retry-After")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None  # format date HTTP : non géré, on ne devine pas


_ERRORS_BY_STATUS: dict[int, tuple[type[APIError], str]] = {
    400: (BadRequestError, "Invalid request"),
    401: (AuthenticationError, "Authentication refused"),
    403: (ForbiddenError, "Access denied (missing scope on the API key?)"),
    404: (NotFoundError, "Resource not found"),
    409: (ConflictError, "Conflict with the current state of the resource"),
    422: (UnprocessableEntityError, "Data rejected by the API"),
    429: (RateLimitError, "Too many requests, retry in a moment"),
}


def error_from_response(
    status_code: int,
    response_text: str,
    context: str,
    headers: Optional[Mapping[str, str]] = None,
) -> APIError:
    """Build the typed exception matching the HTTP code, with a readable message.

    `context` describes the action that failed (e.g. "Token refresh failed").
    """
    if status_code in _ERRORS_BY_STATUS:
        cls, reason = _ERRORS_BY_STATUS[status_code]
    elif 500 <= status_code < 600:
        cls, reason = ServerError, "Volta server error"
    else:
        cls, reason = APIError, "Unexpected HTTP error"
    message = f"{context}: {reason}"
    if cls is RateLimitError:
        return RateLimitError(message, status_code=status_code, response_text=response_text,
                              retry_after=_parse_retry_after(headers))
    return cls(message, status_code=status_code, response_text=response_text)

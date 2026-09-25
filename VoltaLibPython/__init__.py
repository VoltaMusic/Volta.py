from importlib.metadata import PackageNotFoundError, version

from .client import VoltaClient
from .exceptions import (
    APIError,
    AuthenticationError,
    BadRequestError,
    ConfigurationError,
    ConflictError,
    ConnectionFailedError,
    ForbiddenError,
    InvalidArgumentError,
    InvalidResponseError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    RequestTimeoutError,
    ServerError,
    TokenStorageError,
    UnprocessableEntityError,
    VoltaAPIExceptions,
)

try:
    __version__ = version("VoltaLib")
except PackageNotFoundError:  # sources utilisées sans installation (pip install -e . non fait)
    __version__ = "0.0.0"

__all__ = [
    "VoltaClient",
    "__version__",
    "APIError",
    "AuthenticationError",
    "BadRequestError",
    "ConfigurationError",
    "ConflictError",
    "ConnectionFailedError",
    "ForbiddenError",
    "InvalidArgumentError",
    "InvalidResponseError",
    "NetworkError",
    "NotFoundError",
    "RateLimitError",
    "RequestTimeoutError",
    "ServerError",
    "TokenStorageError",
    "UnprocessableEntityError",
    "VoltaAPIExceptions",
]

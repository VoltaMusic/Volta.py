"""Toutes les exceptions que la lib peut lever.

Hiérarchie :

    VoltaAPIExceptions                  base de tout ce que lève la lib
    ├── ConfigurationError              .env incomplet (CLIENT_ID / CLIENT_SECRET)
    ├── InvalidArgumentError            argument invalide, détecté avant tout appel réseau (hérite aussi de ValueError)
    ├── TokenStorageError               lecture / écriture du fichier de token impossible
    ├── NetworkError                    la requête n'a pas pu aboutir (aucune réponse HTTP)
    │   ├── ConnectionFailedError       serveur injoignable (DNS, connexion refusée, SSL...)
    │   └── RequestTimeoutError         pas de réponse dans le délai imparti
    ├── InvalidResponseError            réponse 2xx inexploitable (JSON invalide, champ attendu absent)
    └── APIError                        l'API a répondu avec un code d'erreur HTTP
        ├── BadRequestError             400
        ├── AuthenticationError         401
        ├── ForbiddenError              403 (scope manquant)
        ├── NotFoundError               404
        ├── ConflictError               409
        ├── UnprocessableEntityError    422 (corps de requête refusé)
        ├── RateLimitError              429
        └── ServerError                 5xx
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Optional


class VoltaAPIExceptions(Exception):
    """Classe de base pour les erreurs de la lib."""
    pass

class ConfigurationError(VoltaAPIExceptions):
    """Levée quand la configuration locale est incomplète (ex. CLIENT_ID absent du .env)."""
    pass

class InvalidArgumentError(VoltaAPIExceptions, ValueError):
    """Levée quand un argument passé à une méthode est invalide, avant tout
    appel réseau. Hérite aussi de ValueError pour rester compatible avec
    le code qui attrapait déjà ValueError."""
    pass

class TokenStorageError(VoltaAPIExceptions):
    """Levée quand le fichier de token ne peut pas être lu ou écrit
    (permissions, disque plein, chemin invalide...)."""
    def __init__(self, message: str, path: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.path = path

    def __str__(self) -> str:
        if self.path:
            return f"{self.message}\n  -> fichier : {self.path}"
        return self.message

class NetworkError(VoltaAPIExceptions):
    """Levée quand la requête n'a obtenu aucune réponse HTTP."""
    def __init__(self, message: str, url: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.url = url

    def __str__(self) -> str:
        if self.url:
            return f"{self.message}\n  -> {self.url}"
        return self.message

class ConnectionFailedError(NetworkError):
    """Levée quand le serveur est injoignable (DNS, connexion refusée, SSL...)."""
    pass

class RequestTimeoutError(NetworkError):
    """Levée quand le serveur ne répond pas dans le délai imparti."""
    pass

class InvalidResponseError(VoltaAPIExceptions):
    """Levée quand l'API répond avec succès mais que la réponse est
    inexploitable (JSON invalide, champ attendu absent)."""
    def __init__(self, message: str, response_text: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.response_text = response_text

    def __str__(self) -> str:
        if self.response_text:
            excerpt = self.response_text.strip()[:200]
            return f"{self.message}\n  -> réponse reçue : {excerpt}"
        return self.message

class APIError(VoltaAPIExceptions):
    """Levée quand l'API renvoie un code d'erreur HTTP."""
    def __init__(self, message: str, status_code: int | None = None, response_text: str | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_text = response_text

    @property
    def detail(self) -> str | None:
        """Message d'erreur renvoyé par l'API (champ `detail` du JSON), ou le texte brut."""
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
    """Levée en cas d'erreur 400 (Requête invalide / paramètres manquants)."""
    pass

class AuthenticationError(APIError):
    """Levée en cas d'erreur 401 (Non autorisé / Token invalide)."""
    pass

class ForbiddenError(APIError):
    """Levée en cas d'erreur 403 (Accès refusé, en général un scope manquant)."""
    pass

class NotFoundError(APIError):
    """Levée en cas d'erreur 404 (Ressource introuvable)."""
    pass

class ConflictError(APIError):
    """Levée en cas d'erreur 409 (Conflit, ex. ressource déjà existante)."""
    pass

class UnprocessableEntityError(APIError):
    """Levée en cas d'erreur 422 (Corps de requête refusé par l'API)."""
    pass

class RateLimitError(APIError):
    """Levée en cas d'erreur 429 (Trop de requêtes).

    `retry_after` : nombre de secondes à attendre avant de réessayer, si
    l'API l'a indiqué (header `Retry-After`), sinon None.
    """
    def __init__(self, message: str, status_code: int | None = None, response_text: str | None = None,
                 retry_after: int | None = None):
        super().__init__(message, status_code=status_code, response_text=response_text)
        self.retry_after = retry_after

    def __str__(self) -> str:
        text = super().__str__()
        if self.retry_after is not None:
            text += f"\n  -> réessaie dans {self.retry_after} s"
        return text

class ServerError(APIError):
    """Levée en cas d'erreur serveur (500, 502, 503, 504)."""
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
                parts.append(f"{loc} : {item['msg']}" if loc else str(item["msg"]))
            else:
                parts.append(str(item))
        return " ; ".join(parts)
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
    400: (BadRequestError, "Requête invalide"),
    401: (AuthenticationError, "Authentification refusée"),
    403: (ForbiddenError, "Accès refusé (scope manquant sur la clé API ?)"),
    404: (NotFoundError, "Ressource introuvable"),
    409: (ConflictError, "Conflit avec l'état actuel de la ressource"),
    422: (UnprocessableEntityError, "Données envoyées refusées par l'API"),
    429: (RateLimitError, "Trop de requêtes, réessaie dans quelques instants"),
}


def error_from_response(
    status_code: int,
    response_text: str,
    context: str,
    headers: Optional[Mapping[str, str]] = None,
) -> APIError:
    """Construit l'exception typée adaptée au code HTTP, avec un message lisible.

    `context` décrit l'action qui a échoué (ex. "Échec du rafraîchissement du token").
    """
    if status_code in _ERRORS_BY_STATUS:
        cls, reason = _ERRORS_BY_STATUS[status_code]
    elif 500 <= status_code < 600:
        cls, reason = ServerError, "Erreur du serveur Volta"
    else:
        cls, reason = APIError, "Erreur HTTP inattendue"
    message = f"{context} : {reason}"
    if cls is RateLimitError:
        return RateLimitError(message, status_code=status_code, response_text=response_text,
                              retry_after=_parse_retry_after(headers))
    return cls(message, status_code=status_code, response_text=response_text)

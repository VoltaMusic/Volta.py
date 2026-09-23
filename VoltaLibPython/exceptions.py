from __future__ import annotations

import json


class VoltaAPIExceptions(Exception):
    """Classe de base pour les erreurs de la lib."""
    pass

class ConfigurationError(VoltaAPIExceptions):
    """Levée quand la configuration locale est incomplète (ex. CLIENT_ID absent du .env)."""
    pass

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
                    return str(data[key])
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
    """Levée en cas d'erreur 403 (Accès refusé)."""
    pass

class NotFoundError(APIError):
    """Levée en cas d'erreur 404 (Ressource introuvable)."""
    pass

class RateLimitError(APIError):
    """Levée en cas d'erreur 429 (Trop de requêtes)."""
    pass

class ServerError(APIError):
    """Levée en cas d'erreur serveur (500, 502, 503, 504)."""
    pass


_ERRORS_BY_STATUS: dict[int, tuple[type[APIError], str]] = {
    400: (BadRequestError, "Requête invalide"),
    401: (AuthenticationError, "Authentification refusée"),
    403: (ForbiddenError, "Accès refusé"),
    404: (NotFoundError, "Ressource introuvable"),
    429: (RateLimitError, "Trop de requêtes, réessaie dans quelques instants"),
}


def error_from_response(status_code: int, response_text: str, context: str) -> APIError:
    """Construit l'exception typée adaptée au code HTTP, avec un message lisible.

    `context` décrit l'action qui a échoué (ex. "Échec du rafraîchissement du token").
    """
    if status_code in _ERRORS_BY_STATUS:
        cls, reason = _ERRORS_BY_STATUS[status_code]
    elif 500 <= status_code < 600:
        cls, reason = ServerError, "Erreur du serveur Volta"
    else:
        cls, reason = APIError, "Erreur HTTP inattendue"
    return cls(f"{context} : {reason}", status_code=status_code, response_text=response_text)

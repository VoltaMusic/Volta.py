class VoltaAPIExceptions(Exception):
    """Classe de base pour les erreurs de la lib."""
    pass

class APIError(VoltaAPIExceptions):
    """Levée quand l'API renvoie un code d'erreur HTTP."""
    def __init__(self, message: str, status_code: int | None = None, response_text: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text

class AuthenticationError(APIError):
    """Levée en cas d'erreur 401 (Non autorisé / Token invalide)."""
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
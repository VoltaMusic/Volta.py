from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_TIMEOUT = 20
TOKEN_REFRESH_MARGIN = 30
TOKEN_ENDPOINT = "/api/v1/oauth/token"


def _retry_adapter(*methods: str) -> HTTPAdapter:
    """Adapter qui réessaie jusqu'à 3 fois sur 500/502/503/504, mais
    seulement pour les méthodes `methods`."""
    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=(500, 502, 503, 504),
        allowed_methods=methods,
        # Après les retries, renvoyer la dernière réponse 5xx plutôt que
        # lever une RetryError brute : le client la convertit en ServerError
        # avec le message de l'API.
        raise_on_status=False,
    )
    return HTTPAdapter(max_retries=retries)


def _build_session() -> requests.Session:
    """Session par défaut : seuls les GET sont réessayés.

    Un POST / PUT / DELETE n'est jamais renvoyé automatiquement : un 5xx
    peut arriver *après* que le serveur a déjà traité la requête, et la
    rejouer créerait par exemple une playlist en double.
    """
    session = requests.Session()
    adapter = _retry_adapter("GET")
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _mount_token_retry(session: requests.Session, base_url: str) -> None:
    """Réessaie aussi le POST de l'endpoint de token : demander un jeton
    deux fois n'a aucun effet de bord, contrairement aux autres POST.

    requests choisit l'adapter dont le préfixe d'URL est le plus long, donc
    celui-ci ne s'applique qu'à `{base_url}/api/v1/oauth/token`.
    """
    session.mount(f"{base_url.rstrip('/')}{TOKEN_ENDPOINT}", _retry_adapter("POST"))

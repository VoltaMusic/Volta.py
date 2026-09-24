from __future__ import annotations

from urllib.parse import quote


def segment(value: object) -> str:
    """Encode une valeur pour l'insérer comme un seul segment de chemin
    d'URL : `/`, `?`, `#`, `&`, espaces... sont échappés, pour qu'un ID ne
    puisse jamais changer la route appelée ni ajouter des paramètres."""
    return quote(str(value), safe="")

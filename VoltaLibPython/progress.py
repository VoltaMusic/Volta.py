from __future__ import annotations

import sys
import threading
import time
from typing import Optional

SPINNER_MIN_DELAY = 0.3


class _Spinner:
    """Petit indicateur de chargement affiché dans le terminal pendant
    qu'une requête est en cours, pour rassurer que ça tourne encore et que
    ce n'est pas figé.

    - Ne s'affiche que si la requête dépasse `SPINNER_MIN_DELAY` secondes
      (les requêtes rapides ne clignotent pas à l'écran).
    - Ne s'active jamais si la sortie standard n'est pas un vrai terminal
      (redirection vers un fichier, pipe, capture par pytest...), pour ne
      jamais polluer des logs avec des caractères de contrôle `\\r`.
    - Tourne dans un thread daemon séparé, arrêté proprement à la sortie
      du `with`.
    """

    FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, message: str) -> None:
        self._message = message
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._enabled = sys.stdout.isatty()

    def __enter__(self) -> "_Spinner":
        if self._enabled:
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._spin, daemon=True)
            self._thread.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        if self._thread is not None:
            self._stop_event.set()
            self._thread.join(timeout=1)
            # Efface la ligne du spinner (si elle a eu le temps de s'afficher).
            sys.stdout.write("\r" + " " * (len(self._message) + 4) + "\r")
            sys.stdout.flush()

    def _spin(self) -> None:
        start = time.monotonic()
        i = 0
        while not self._stop_event.is_set():
            if time.monotonic() - start >= SPINNER_MIN_DELAY:
                frame = self.FRAMES[i % len(self.FRAMES)]
                sys.stdout.write(f"\r{frame} {self._message}...")
                sys.stdout.flush()
                i += 1
            time.sleep(0.1)

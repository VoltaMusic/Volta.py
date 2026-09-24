from __future__ import annotations

import sys
import threading
from typing import Optional, TextIO

SPINNER_MIN_DELAY = 0.3
SPINNER_INTERVAL = 0.1

_UNICODE_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
_ASCII_FRAMES = "|/-\\"


def _is_terminal(stream: Optional[TextIO]) -> bool:
    """True seulement pour un vrai terminal. `stream` peut être None
    (pythonw, service Windows) ou ne pas avoir de `isatty()`."""
    try:
        return stream is not None and stream.isatty()
    except (AttributeError, ValueError):  # ValueError : flux déjà fermé
        return False


def _frames_for(stream: TextIO) -> str:
    """Les caractères braille si le terminal sait les afficher, sinon une
    version ASCII (ex. console Windows en cp1252)."""
    try:
        _UNICODE_FRAMES.encode(getattr(stream, "encoding", None) or "ascii")
        return _UNICODE_FRAMES
    except (UnicodeEncodeError, LookupError):
        return _ASCII_FRAMES


class _Spinner:
    """Petit indicateur de chargement affiché dans le terminal pendant
    qu'une requête est en cours, pour rassurer que ça tourne encore et que
    ce n'est pas figé.

    - Ne s'affiche que si la requête dépasse `SPINNER_MIN_DELAY` secondes
      (les requêtes rapides ne clignotent pas à l'écran).
    - N'ajoute aucune latence : la sortie du `with` réveille le thread
      immédiatement au lieu d'attendre la fin d'un `sleep`.
    - Écrit sur stderr, pour ne jamais polluer la sortie standard d'un
      programme (pipe, redirection vers un fichier).
    - Ne s'active jamais si stderr n'est pas un vrai terminal (capture par
      pytest, logs...), pour ne pas écrire de caractères de contrôle `\\r`.
    """

    def __init__(self, message: str, stream: Optional[TextIO] = None) -> None:
        self._message = message
        self._stream = stream if stream is not None else sys.stderr
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._shown = False
        self._enabled = _is_terminal(self._stream)

    def __enter__(self) -> "_Spinner":
        if self._enabled:
            self._thread = threading.Thread(target=self._spin, daemon=True)
            self._thread.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        if self._thread is None:
            return
        self._stop_event.set()
        self._thread.join()
        if self._shown:
            # Efface la ligne du spinner.
            self._write("\r" + " " * (len(self._message) + 5) + "\r")

    def _write(self, text: str) -> None:
        try:
            self._stream.write(text)
            self._stream.flush()
        except (OSError, ValueError):
            pass  # terminal fermé entre-temps : l'affichage n'est pas critique

    def _spin(self) -> None:
        # Requête terminée avant le délai : on sort sans jamais rien afficher.
        if self._stop_event.wait(SPINNER_MIN_DELAY):
            return
        frames = _frames_for(self._stream)
        i = 0
        while True:
            self._write(f"\r{frames[i % len(frames)]} {self._message}...")
            self._shown = True
            i += 1
            if self._stop_event.wait(SPINNER_INTERVAL):
                return

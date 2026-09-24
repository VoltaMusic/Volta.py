"""
Tests du spinner (_Spinner).

Lancer avec : pytest tests/test_progress.py -v
"""

from __future__ import annotations

import io
import time

import pytest

from VoltaLibPython import progress
from VoltaLibPython.progress import _Spinner


class FakeTerminal(io.StringIO):
    def __init__(self, encoding: str = "utf-8", tty: bool = True) -> None:
        super().__init__()
        self._encoding = encoding
        self._tty = tty

    @property
    def encoding(self) -> str:
        return self._encoding

    def isatty(self) -> bool:
        return self._tty


@pytest.fixture
def fast_spinner(monkeypatch):
    monkeypatch.setattr(progress, "SPINNER_MIN_DELAY", 0.05)
    monkeypatch.setattr(progress, "SPINNER_INTERVAL", 0.01)


class TestSpinner:
    def test_fast_request_adds_no_latency_and_prints_nothing(self):
        stream = FakeTerminal()
        start = time.perf_counter()
        with _Spinner("GET /x", stream=stream):
            pass
        assert time.perf_counter() - start < 0.05
        assert stream.getvalue() == ""

    def test_slow_request_shows_then_clears_the_line(self, fast_spinner):
        stream = FakeTerminal()
        with _Spinner("GET /x", stream=stream):
            time.sleep(0.15)
        output = stream.getvalue()
        assert "GET /x..." in output
        assert output.endswith("\r")  # ligne effacée à la sortie

    def test_non_terminal_never_starts_a_thread(self, fast_spinner):
        stream = FakeTerminal(tty=False)
        spinner = _Spinner("GET /x", stream=stream)
        with spinner:
            time.sleep(0.1)
        assert spinner._thread is None
        assert stream.getvalue() == ""

    def test_none_stream_is_treated_as_non_terminal(self, monkeypatch):
        # pythonw / service Windows : sys.stderr vaut None.
        monkeypatch.setattr("sys.stderr", None)
        with _Spinner("GET /x") as spinner:
            pass
        assert spinner._thread is None

    def test_ascii_fallback_when_terminal_cannot_encode_braille(self, fast_spinner):
        stream = FakeTerminal(encoding="cp1252")
        with _Spinner("GET /x", stream=stream):
            time.sleep(0.1)
        output = stream.getvalue()
        assert "⠋" not in output
        assert any(frame in output for frame in "|/-\\")

    def test_exception_inside_block_still_stops_the_spinner(self, fast_spinner):
        stream = FakeTerminal()
        spinner = _Spinner("GET /x", stream=stream)
        with pytest.raises(RuntimeError):
            with spinner:
                raise RuntimeError("boom")
        assert not spinner._thread.is_alive()

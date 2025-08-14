import threading
from typing import Callable, Optional

import requests
from kivy.clock import Clock


def is_online(timeout: float = 2.0) -> bool:
    try:
        requests.get("https://clients3.google.com/generate_204", timeout=timeout)
        return True
    except Exception:
        try:
            requests.get("https://1.1.1.1", timeout=timeout)
            return True
        except Exception:
            return False


class ConnectivityMonitor:
    """Polls connectivity and triggers a callback when the status flips."""

    def __init__(self, interval_seconds: float = 10.0) -> None:
        self.interval_seconds = interval_seconds
        self._online = False
        self._event = None
        self._callback: Optional[Callable[[bool], None]] = None

    def start(self, callback: Callable[[bool], None]) -> None:
        self._callback = callback
        self._online = is_online()
        self._event = Clock.schedule_interval(self._tick, self.interval_seconds)

    def stop(self) -> None:
        if self._event is not None:
            self._event.cancel()
            self._event = None

    def _tick(self, *_args) -> None:
        status = is_online()
        if status != self._online:
            self._online = status
            if self._callback:
                try:
                    self._callback(status)
                except Exception:
                    pass
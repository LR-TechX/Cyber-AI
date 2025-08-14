from typing import Callable, Optional

from kivy.clock import Clock


class ScanScheduler:
    def __init__(self, run_scan_callable: Callable[[], None]) -> None:
        self.run_scan_callable = run_scan_callable
        self._event = None
        self._minutes = 60.0
        self._enabled = False

    def set_interval_minutes(self, minutes: float) -> None:
        if minutes <= 0:
            self.stop()
            self._minutes = 0.0
            return
        self._minutes = max(5.0, minutes)
        if self._enabled:
            self.stop()
            self.start()

    def start(self) -> None:
        if self._event is not None or self._minutes <= 0:
            return
        self._enabled = True
        self._event = Clock.schedule_interval(lambda _dt: self.run_scan_callable(), self._minutes * 60.0)

    def stop(self) -> None:
        if self._event is not None:
            self._event.cancel()
            self._event = None
        self._enabled = False

    def is_running(self) -> bool:
        return self._event is not None
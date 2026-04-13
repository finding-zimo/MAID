"""Screen capture via mss running in a background thread."""

from __future__ import annotations

import logging
import threading
import time
from typing import TYPE_CHECKING

import mss
import mss.tools

if TYPE_CHECKING:
    from maid.config import Settings

logger = logging.getLogger(__name__)


class ScreenCapture:
    """Captures the configured monitor on a fixed interval.

    The latest frame is stored as raw PNG bytes. Callers read it via
    ``get_latest()``. Old frames are silently replaced — there is no queue.
    """

    def __init__(self, settings: Settings) -> None:
        self._monitor_index = settings.monitor_index
        self._interval = settings.capture_interval_seconds
        self._latest: bytes | None = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._capture_loop, daemon=True, name="screen-capture")
        self._thread.start()
        logger.debug("Screen capture started (monitor %d, interval %.1fs)", self._monitor_index, self._interval)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def get_latest(self) -> bytes | None:
        """Return the most recently captured frame as PNG bytes, or None."""
        with self._lock:
            return self._latest

    def _capture_loop(self) -> None:
        with mss.mss() as sct:
            # mss monitor list: index 0 = all monitors combined, 1+ = individual.
            monitors = sct.monitors
            idx = self._monitor_index + 1  # shift to mss 1-based index
            if idx >= len(monitors):
                logger.warning(
                    "Monitor index %d out of range (%d monitors). Falling back to primary.",
                    self._monitor_index,
                    len(monitors) - 1,
                )
                idx = 1

            monitor = monitors[idx]
            logger.debug("Capturing monitor %d: %dx%d", idx, monitor["width"], monitor["height"])

            while not self._stop_event.is_set():
                try:
                    screenshot = sct.grab(monitor)
                    png_bytes = mss.tools.to_png(screenshot.rgb, screenshot.size)

                    with self._lock:
                        self._latest = png_bytes

                except Exception:
                    logger.exception("Screen capture error")

                time.sleep(self._interval)

"""Background thread that watches for config file changes."""

from __future__ import annotations

import os
import threading


class ConfigWatcher:
    def __init__(self, config_path: str | None) -> None:
        from plmux.config.loader import _resolve_user_config_path
        self._path = _resolve_user_config_path(config_path)
        self._mtime: float = 0.0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._update_mtime()

    def _update_mtime(self) -> None:
        try:
            self._mtime = os.path.getmtime(self._path)
        except OSError:
            pass

    def start(self, callback: object) -> None:
        def _watch() -> None:
            while not self._stop.is_set():
                self._stop.wait(2.0)
                if self._stop.is_set():
                    break
                try:
                    current = os.path.getmtime(self._path)
                    if current > self._mtime:
                        self._mtime = current
                        callback()
                except OSError:
                    pass

        self._thread = threading.Thread(target=_watch, name="plmux-config-watcher", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

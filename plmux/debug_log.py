"""Async file debug logging (enable with --debug flag only)."""

from __future__ import annotations

import logging
import os
import queue
import threading
from pathlib import Path
from typing import Any, Optional

_logger: Optional[logging.Logger] = None
_log_path: Optional[Path] = None
_log_queue: queue.Queue[logging.LogRecord | None] = queue.Queue()
_log_thread: Optional[threading.Thread] = None
_log_running: bool = False


class _QueueHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        if _log_running:
            try:
                _log_queue.put_nowait(record)
            except queue.Full:
                pass


def _log_worker() -> None:
    global _log_running
    _log_running = True
    while True:
        try:
            record = _log_queue.get(timeout=0.5)
        except queue.Empty:
            continue
        if record is None:
            break
        if _logger is not None:
            for handler in _logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    try:
                        handler.emit(record)
                        handler.flush()
                    except Exception:
                        pass


def is_debug_enabled(explicit: bool | None = None) -> bool:
    if explicit is not None:
        return explicit
    return _logger is not None


def setup_debug_logging(enabled: bool, base_dir: str | None = None) -> Optional[Path]:
    global _logger, _log_path, _log_thread, _log_running
    if not enabled:
        return None
    if _logger is not None:
        return _log_path
    base = Path(base_dir or os.getcwd()).resolve()
    _log_path = base / "plmux_debug.log"
    _log_path.parent.mkdir(parents=True, exist_ok=True)

    _logger = logging.getLogger("plmux.debug")
    _logger.setLevel(logging.DEBUG)
    _logger.handlers.clear()

    fh = logging.FileHandler(_log_path, encoding="utf-8", mode="a")
    fh.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh.setFormatter(fmt)
    _logger.addHandler(fh)

    qh = _QueueHandler()
    qh.setLevel(logging.DEBUG)
    qh.setFormatter(fmt)
    _logger.addHandler(qh)

    _logger.propagate = False

    _log_running = True

    _log_thread = threading.Thread(target=_log_worker, daemon=True, name="plmux-log")
    _log_thread.start()

    return _log_path


def shutdown_debug_logging() -> None:
    global _log_running
    _log_running = False
    try:
        _log_queue.put_nowait(None)
    except queue.Full:
        pass


def dbg(msg: str, *args: Any) -> None:
    if _logger is not None:
        _logger.debug(msg, *args)


def debug_level() -> int:
    if _logger is None:
        return 0
    return 1


def logging_active() -> bool:
    return _logger is not None


def win_dbg(msg: str, *args: Any) -> None:
    if _logger is not None and os.name == "nt":
        _logger.debug("[WIN] " + msg, *args)

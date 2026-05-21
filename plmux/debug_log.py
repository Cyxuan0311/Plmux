"""Async file debug logging (enable with --debug flag only)."""

from __future__ import annotations

import logging
import os
import queue
import sys
import threading
import time
from collections import defaultdict
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


class PerfTimer:
    __slots__ = ("_start",)

    def __init__(self) -> None:
        self._start = time.perf_counter()

    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self._start) * 1000.0

    def elapsed_us(self) -> float:
        return (time.perf_counter() - self._start) * 1_000_000.0

    def lap(self, label: str) -> None:
        if _logger is None:
            return
        ms = self.elapsed_ms()
        _logger.debug("PERF %s: %.3f ms", label, ms)

    def reset(self) -> None:
        self._start = time.perf_counter()


class PerfStats:
    __slots__ = ("_name", "_count", "_total_ms", "_min_ms", "_max_ms", "_last_report")

    def __init__(self, name: str) -> None:
        self._name = name
        self._count = 0
        self._total_ms = 0.0
        self._min_ms = float("inf")
        self._max_ms = 0.0
        self._last_report = time.monotonic()

    def record(self, ms: float) -> None:
        self._count += 1
        self._total_ms += ms
        if ms < self._min_ms:
            self._min_ms = ms
        if ms > self._max_ms:
            self._max_ms = ms

    def report(self, interval_s: float = 5.0) -> None:
        if _logger is None:
            return
        now = time.monotonic()
        if now - self._last_report < interval_s:
            return
        self._last_report = now
        if self._count == 0:
            return
        avg = self._total_ms / self._count
        _logger.debug(
            "STATS [%s] count=%d avg=%.3fms min=%.3fms max=%.3fms total=%.1fms",
            self._name, self._count, avg, self._min_ms, self._max_ms, self._total_ms,
        )

    def reset(self) -> None:
        self._count = 0
        self._total_ms = 0.0
        self._min_ms = float("inf")
        self._max_ms = 0.0


class FrameProfiler:
    __slots__ = ("_phases", "_frame_count", "_last_report", "_slow_threshold_ms", "_exclude_from_slow")

    def __init__(self, slow_threshold_ms: float = 16.0, exclude_from_slow: set[str] | None = None) -> None:
        self._phases: dict[str, PerfStats] = {}
        self._frame_count = 0
        self._last_report = time.monotonic()
        self._slow_threshold_ms = slow_threshold_ms
        self._exclude_from_slow = exclude_from_slow or set()

    def phase(self, name: str) -> PerfStats:
        if name not in self._phases:
            self._phases[name] = PerfStats(f"frame.{name}")
        return self._phases[name]

    def end_frame(self, phase_times: dict[str, float]) -> None:
        self._frame_count += 1
        total = 0.0
        slow_total = 0.0
        for name, ms in phase_times.items():
            self.phase(name).record(ms)
            total += ms
            if name not in self._exclude_from_slow:
                slow_total += ms

        if _logger is None:
            return

        if slow_total > self._slow_threshold_ms:
            parts = " ".join(f"{n}={v:.1f}ms" for n, v in phase_times.items())
            _logger.debug("SLOW_FRAME #%d total=%.1fms slow=%.1fms %s",
                          self._frame_count, total, slow_total, parts)

        if self._frame_count % 60 == 0:
            now = time.monotonic()
            if now - self._last_report >= 5.0:
                self._last_report = now
                for name, stats in self._phases.items():
                    stats.report(interval_s=0.0)
                for name, stats in self._phases.items():
                    stats.reset()


_frame_profiler: FrameProfiler | None = None


def get_frame_profiler(slow_threshold_ms: float = 16.0, exclude_from_slow: set[str] | None = None) -> FrameProfiler:
    global _frame_profiler
    if _frame_profiler is None:
        _frame_profiler = FrameProfiler(slow_threshold_ms=slow_threshold_ms, exclude_from_slow=exclude_from_slow)
    return _frame_profiler


def perf_dbg(msg: str, *args: Any) -> None:
    if _logger is not None:
        _logger.debug("PERF " + msg, *args)


def win_dbg(msg: str, *args: Any) -> None:
    if _logger is not None and os.name == "nt":
        _logger.debug("[WIN] " + msg, *args)
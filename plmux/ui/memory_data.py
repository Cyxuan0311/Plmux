"""Cross-platform memory data collection for plmux processes."""

from __future__ import annotations

import os
import platform
import time
from typing import Any

_HAS_PSUTIL = False
try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    pass

_cache: dict[str, Any] = {}
_cache_ts: float = 0.0
_cache_ttl: float = 2.0


def _read_proc_status(pid: int) -> dict[str, int]:
    result: dict[str, int] = {"rss": 0, "vms": 0}
    try:
        with open(f"/proc/{pid}/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    val = line.split()[1]
                    result["rss"] = int(val) * 1024
                elif line.startswith("VmSize:"):
                    val = line.split()[1]
                    result["vms"] = int(val) * 1024
                elif line.startswith("VmPeak:"):
                    val = line.split()[1]
                    result["peak"] = int(val) * 1024
    except (OSError, IOError, ValueError, IndexError):
        pass
    return result


def _get_memory_proc_self() -> dict[str, int]:
    return _read_proc_status(os.getpid())


def _get_memory_psutil(pid: int | None = None) -> dict[str, int]:
    result: dict[str, int] = {"rss": 0, "vms": 0}
    try:
        p = psutil.Process(os.getpid() if pid is None else pid)
        mem = p.memory_info()
        result["rss"] = getattr(mem, "rss", 0)
        result["vms"] = getattr(mem, "vms", 0)
    except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
        pass
    return result


def _get_memory_macos_self() -> dict[str, int]:
    import resource
    result: dict[str, int] = {"rss": 0, "vms": 0}
    try:
        ru = resource.getrusage(resource.RUSAGE_SELF)
        result["rss"] = ru.ru_maxrss * 1024
    except (AttributeError, ValueError):
        pass
    return result


def _get_memory_macos_child(pid: int) -> dict[str, int]:
    result: dict[str, int] = {"rss": 0, "vms": 0}
    try:
        import subprocess
        out = subprocess.check_output(
            ["ps", "-o", "rss=", "-p", str(pid)],
            timeout=2, text=True,
        ).strip()
        if out:
            result["rss"] = int(out) * 1024
    except (subprocess.SubprocessError, ValueError, OSError):
        pass
    return result


def _get_memory_windows_child(pid: int) -> dict[str, int]:
    if _HAS_PSUTIL:
        return _get_memory_psutil(pid)
    result: dict[str, int] = {"rss": 0, "vms": 0}
    try:
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        PROCESS_QUERY_INFORMATION = 0x0400
        PROCESS_VM_READ = 0x0010
        handle = kernel32.OpenProcess(
            PROCESS_QUERY_INFORMATION | PROCESS_VM_READ,
            False, pid,
        )
        if handle:
            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]
            pmc = PROCESS_MEMORY_COUNTERS()
            if kernel32.GetProcessMemoryInfo(handle, ctypes.byref(pmc), ctypes.sizeof(pmc)):
                result["rss"] = pmc.WorkingSetSize
                result["vms"] = pmc.PagefileUsage
            kernel32.CloseHandle(handle)
    except Exception:
        pass
    return result


def get_process_memory(pid: int | None = None) -> dict[str, int]:
    systype = platform.system()
    if pid is None or pid == os.getpid():
        pid = os.getpid()

    if _HAS_PSUTIL:
        return _get_memory_psutil(pid)

    if pid == os.getpid():
        if systype == "Linux":
            return _get_memory_proc_self()
        elif systype == "Darwin":
            return _get_memory_macos_self()
        else:
            return _get_memory_psutil(pid) if _HAS_PSUTIL else {"rss": 0, "vms": 0}

    if systype == "Linux":
        return _read_proc_status(pid)
    elif systype == "Darwin":
        return _get_memory_macos_child(pid)
    elif systype == "Windows":
        return _get_memory_windows_child(pid)

    return {"rss": 0, "vms": 0}


def get_system_memory() -> dict[str, int]:
    result: dict[str, int] = {"total": 0, "available": 0, "used": 0}
    if _HAS_PSUTIL:
        mem = psutil.virtual_memory()
        result["total"] = mem.total
        result["available"] = mem.available
        result["used"] = mem.used
        return result
    if platform.system() == "Linux":
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        result["total"] = int(line.split()[1]) * 1024
                    elif line.startswith("MemAvailable:"):
                        result["available"] = int(line.split()[1]) * 1024
                    elif line.startswith("MemFree:"):
                        if "available" not in result or result["available"] == 0:
                            result["available"] = int(line.split()[1]) * 1024
            result["used"] = result["total"] - result["available"]
        except (OSError, IOError, ValueError):
            pass
    return result


def collect_pane_cmd(pane: Any) -> str:
    try:
        cmd = pane.current_command
        if cmd:
            return cmd
    except Exception:
        pass
    try:
        if pane.proc is not None:
            pid = pane.proc.pid
            if _HAS_PSUTIL:
                try:
                    return psutil.Process(pid).name() or str(pid)
                except Exception:
                    pass
            if platform.system() == "Linux":
                try:
                    with open(f"/proc/{pid}/cmdline", "rb") as f:
                        raw = f.read(4096)
                    if raw:
                        parts = raw.split(b"\x00")
                        for p in parts:
                            decoded = p.decode("utf-8", errors="replace")
                            dn = os.path.basename(decoded)
                            if dn:
                                return dn
                except (OSError, IOError):
                    pass
    except Exception:
        pass
    return "?"


def clear_memory_cache() -> None:
    global _cache, _cache_ts
    _cache = {}
    _cache_ts = 0.0


def collect_all_pane_memory(ws: Any, *, force: bool = False) -> dict[str, Any]:
    """Collect memory data for plmux and all pane processes.

    Results are cached for 2 seconds to avoid repeated /proc reads.

    Returns:
    {
        "self": {"rss": ..., "vms": ..., "name": "plmux", "pct": ...},
        "system": {"total": ..., "available": ..., "used": ...},
        "sessions": [
            {
                "name": "session_name",
                "windows": [
                    {
                        "name": "window_name",
                        "panes": [
                            {"index": 0, "pid": ..., "cmd": ..., "rss": ..., "vms": ..., "pct": ...},
                        ],
                        "total_rss": ..., "total_pct": ...,
                    },
                ],
                "total_rss": ..., "total_pct": ...,
            },
        ],
        "total_rss": ..., "total_pct": ...,
    }
    """
    global _cache, _cache_ts
    now = time.monotonic()
    if not force and _cache and now - _cache_ts < _cache_ttl:
        return _cache

    sys_mem = get_system_memory()
    sys_total = sys_mem.get("total", 1) or 1

    self_mem = get_process_memory()
    self_rss = self_mem.get("rss", 0)
    result: dict[str, Any] = {
        "self": {
            "rss": self_rss,
            "vms": self_mem.get("vms", 0),
            "name": "plmux",
            "pct": (self_rss / sys_total) * 100,
        },
        "system": sys_mem,
        "sessions": [],
        "total_rss": self_rss,
        "total_pct": (self_rss / sys_total) * 100,
    }

    total = self_rss

    try:
        for sess in ws.sessions_list:
            sess_data: dict[str, Any] = {
                "name": getattr(sess, "name", "session"),
                "windows": [],
                "total_rss": 0,
                "total_pct": 0.0,
            }
            sess_total = 0
            for win_idx, win in enumerate(getattr(sess, "windows", [])):
                win_data: dict[str, Any] = {
                    "name": getattr(win, "name", f"W{win_idx}"),
                    "panes": [],
                    "total_rss": 0,
                    "total_pct": 0.0,
                }
                win_total = 0
                for pane in getattr(win, "panes", []):
                    pid = -1
                    try:
                        if pane.proc is not None:
                            pid = pane.proc.pid
                    except Exception:
                        pass
                    pane_mem = get_process_memory(pid) if pid > 0 else {"rss": 0, "vms": 0}
                    pane_rss = pane_mem.get("rss", 0)
                    pane_cmd = collect_pane_cmd(pane)
                    pane_data = {
                        "index": len(win_data["panes"]),
                        "pid": pid,
                        "cmd": pane_cmd,
                        "rss": pane_rss,
                        "vms": pane_mem.get("vms", 0),
                        "pct": (pane_rss / sys_total) * 100,
                    }
                    win_data["panes"].append(pane_data)
                    win_total += pane_rss
                win_data["total_rss"] = win_total
                win_data["total_pct"] = (win_total / sys_total) * 100
                sess_data["windows"].append(win_data)
                sess_total += win_total
            sess_data["total_rss"] = sess_total
            sess_data["total_pct"] = (sess_total / sys_total) * 100
            result["sessions"].append(sess_data)
            total += sess_total
    except Exception:
        pass

    result["total_rss"] = total
    result["total_pct"] = (total / sys_total) * 100

    _cache = result
    _cache_ts = time.monotonic()
    return result

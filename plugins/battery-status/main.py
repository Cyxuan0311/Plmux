"""Battery & CPU status plugin for plmux status bar.

Shows the current battery percentage, charging state, and CPU usage
on the right side of the status bar.
Supports Linux (sysfs/proc), macOS (pmset/top), and Windows (wmic).
Results are cached with a 10-second TTL to avoid excessive system calls.
"""

import os
import subprocess
import sys
import time

from plmux.extensions import register_hook, register_status_item, ExtensionContext, plugin_metadata

plugin_metadata(
    name="battery-status",
    version="1.1.0",
    author="plmux",
    description="Show battery percentage, charging state & CPU usage in status bar",
    config_schema={
        "cache_ttl": {"type": "float", "default": 10.0, "description": "Cache TTL in seconds"},
        "show_cpu": {"type": "bool", "default": True, "description": "Show CPU usage indicator"},
    },
)

_BAT_PREFIX = "bat:"
_CPU_PREFIX = "cpu:"

_STYLE_CHARGING = "bold #85c751 on #75715e"
_STYLE_DISCHARGING_HIGH = "bold #85c751 on #75715e"
_STYLE_DISCHARGING_MID = "bold #fabd2f on #75715e"
_STYLE_DISCHARGING_LOW = "bold #f92672 on #75715e"
_STYLE_CPU_LOW = "bold #85c751 on #75715e"
_STYLE_CPU_MID = "bold #fabd2f on #75715e"
_STYLE_CPU_HIGH = "bold #f92672 on #75715e"

_CACHE_TTL = 10.0

_bat_cache: tuple[float, tuple[str, str] | None] = (0.0, None)
_cpu_cache: tuple[float, tuple[str, str] | None] = (0.0, None)
_cpu_prev_stat: tuple[float, tuple[int, int] | None] = (0.0, None)


def _read_battery_linux() -> tuple[str, str] | None:
    try:
        entries = sorted(os.listdir("/sys/class/power_supply"))
    except Exception:
        return None

    bat_dir = None
    for entry in entries:
        path = f"/sys/class/power_supply/{entry}"
        try:
            with open(f"{path}/type") as f:
                if f.read().strip() != "Battery":
                    continue
        except Exception:
            continue
        bat_dir = path
        break

    if bat_dir is None:
        return None

    try:
        with open(f"{bat_dir}/capacity") as f:
            pct = int(f.read().strip())
        with open(f"{bat_dir}/status") as f:
            status = f.read().strip()
    except Exception:
        return None

    if status in ("Charging", "Not charging", "Full"):
        icon = "\u26A1"
        style = _STYLE_CHARGING
    elif status == "Discharging":
        if pct > 60:
            icon = "\u25CF"
            style = _STYLE_DISCHARGING_HIGH
        elif pct > 25:
            icon = "\u25D0"
            style = _STYLE_DISCHARGING_MID
        else:
            icon = "\u25CB"
            style = _STYLE_DISCHARGING_LOW
    else:
        if pct > 60:
            icon = "\u25CF"
            style = _STYLE_DISCHARGING_HIGH
        elif pct > 25:
            icon = "\u25D0"
            style = _STYLE_DISCHARGING_MID
        else:
            icon = "\u25CB"
            style = _STYLE_DISCHARGING_LOW

    label = f"{icon}{pct}%"
    return (f"{_BAT_PREFIX}{label}", style)


def _read_battery_macos() -> tuple[str, str] | None:
    try:
        r = subprocess.run(
            ["pmset", "-g", "batt"],
            capture_output=True,
            text=True,
            timeout=2,
        )
    except Exception:
        return None

    for line in r.stdout.splitlines():
        if "%" not in line:
            continue
        parts = line.split()
        pct_str = ""
        charging = False
        for p in parts:
            if "%" in p:
                pct_str = p.replace(";", "").replace("%", "")
            if "charging" in p.lower() or "charged" in p.lower() or "AC" in p:
                charging = True

        try:
            pct = int(pct_str)
        except ValueError:
            continue

        if charging:
            icon = "\u26A1"
            style = _STYLE_CHARGING
        else:
            if pct > 60:
                icon = "\u25CF"
                style = _STYLE_DISCHARGING_HIGH
            elif pct > 25:
                icon = "\u25D0"
                style = _STYLE_DISCHARGING_MID
            else:
                icon = "\u25CB"
                style = _STYLE_DISCHARGING_LOW

        label = f"{icon}{pct}%"
        return (f"{_BAT_PREFIX}{label}", style)

    return None


def _read_battery_windows() -> tuple[str, str] | None:
    try:
        r = subprocess.run(
            ["wmic", "path", "Win32_Battery", "get", "EstimatedChargeRemaining,BatteryStatus",
             "/format:list"],
            capture_output=True,
            text=True,
            timeout=3,
        )
    except Exception:
        return None

    pct = None
    status = None
    for line in r.stdout.splitlines():
        line = line.strip()
        if line.startswith("EstimatedChargeRemaining="):
            try:
                pct = int(line.split("=", 1)[1])
            except ValueError:
                pass
        elif line.startswith("BatteryStatus="):
            try:
                status = int(line.split("=", 1)[1])
            except ValueError:
                pass

    if pct is None:
        return None

    if status in (2, 6, 7, 8, 9):
        icon = "\u26A1"
        style = _STYLE_CHARGING
    else:
        if pct > 60:
            icon = "\u25CF"
            style = _STYLE_DISCHARGING_HIGH
        elif pct > 25:
            icon = "\u25D0"
            style = _STYLE_DISCHARGING_MID
        else:
            icon = "\u25CB"
            style = _STYLE_DISCHARGING_LOW

    label = f"{icon}{pct}%"
    return (f"{_BAT_PREFIX}{label}", style)


def _read_battery() -> tuple[str, str] | None:
    platform = sys.platform
    if platform == "linux":
        return _read_battery_linux()
    elif platform == "darwin":
        return _read_battery_macos()
    elif platform == "win32":
        return _read_battery_windows()
    return None


def _read_cpu_linux() -> tuple[str, str] | None:
    global _cpu_prev_stat
    try:
        with open("/proc/stat") as f:
            line = f.readline()
    except Exception:
        return None

    parts = line.split()
    if len(parts) < 5:
        return None

    try:
        vals = [int(x) for x in parts[1:5]]
    except ValueError:
        return None

    idle = vals[3]
    total = sum(vals)

    now = time.monotonic()
    prev_time, prev_vals = _cpu_prev_stat
    _cpu_prev_stat = (now, (idle, total))

    if prev_vals is None or now - prev_time < 0.1:
        return None

    prev_idle, prev_total = prev_vals
    d_idle = idle - prev_idle
    d_total = total - prev_total

    if d_total <= 0:
        return None

    pct = round((1 - d_idle / d_total) * 100)
    pct = max(0, min(100, pct))

    if pct > 80:
        style = _STYLE_CPU_HIGH
    elif pct > 50:
        style = _STYLE_CPU_MID
    else:
        style = _STYLE_CPU_LOW

    return (f"{_CPU_PREFIX}\u25B2{pct}%", style)


def _read_cpu_macos() -> tuple[str, str] | None:
    try:
        r = subprocess.run(
            ["top", "-l", "1", "-n", "0", "-s", "0"],
            capture_output=True,
            text=True,
            timeout=3,
        )
    except Exception:
        return None

    for line in r.stdout.splitlines():
        if "CPU usage:" not in line:
            continue
        parts = line.split("CPU usage:")[1].strip()
        user_pct = 0.0
        for segment in parts.split(","):
            segment = segment.strip()
            if "user" in segment:
                try:
                    user_pct = float(segment.split("%")[0])
                except (ValueError, IndexError):
                    pass

        pct = round(user_pct)
        pct = max(0, min(100, pct))

        if pct > 80:
            style = _STYLE_CPU_HIGH
        elif pct > 50:
            style = _STYLE_CPU_MID
        else:
            style = _STYLE_CPU_LOW

        return (f"{_CPU_PREFIX}\u25B2{pct}%", style)

    return None


def _read_cpu_windows() -> tuple[str, str] | None:
    try:
        r = subprocess.run(
            ["wmic", "cpu", "get", "loadpercentage", "/value"],
            capture_output=True,
            text=True,
            timeout=3,
        )
    except Exception:
        return None

    for line in r.stdout.splitlines():
        line = line.strip()
        if line.startswith("LoadPercentage="):
            try:
                pct = int(line.split("=", 1)[1])
            except (ValueError, IndexError):
                return None

            pct = max(0, min(100, pct))

            if pct > 80:
                style = _STYLE_CPU_HIGH
            elif pct > 50:
                style = _STYLE_CPU_MID
            else:
                style = _STYLE_CPU_LOW

            return (f"{_CPU_PREFIX}\u25B2{pct}%", style)

    return None


def _read_cpu() -> tuple[str, str] | None:
    platform = sys.platform
    if platform == "linux":
        return _read_cpu_linux()
    elif platform == "darwin":
        return _read_cpu_macos()
    elif platform == "win32":
        return _read_cpu_windows()
    return None


def refresh_status(ctx: ExtensionContext) -> None:
    global _bat_cache, _cpu_cache
    now = time.monotonic()

    bat_ts, cached_bat = _bat_cache
    if now - bat_ts < _CACHE_TTL:
        if cached_bat is not None:
            register_status_item(cached_bat[0], cached_bat[1], position="right")
    else:
        result = _read_battery()
        _bat_cache = (now, result)
        if result is not None:
            register_status_item(result[0], result[1], position="right")

    cpu_ts, cached_cpu = _cpu_cache
    if now - cpu_ts < _CACHE_TTL:
        if cached_cpu is not None:
            register_status_item(cached_cpu[0], cached_cpu[1], position="right")
    else:
        result = _read_cpu()
        _cpu_cache = (now, result)
        if result is not None:
            register_status_item(result[0], result[1], position="right")


register_hook("status_refresh", refresh_status)
register_hook("app_started", refresh_status)

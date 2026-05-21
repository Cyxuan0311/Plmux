"""Battery status plugin for plmux status bar.

Shows the current battery percentage and charging state on the right side
of the status bar. Supports Linux (UPower/sysfs) and macOS (pmset).
Results are cached with a 10-second TTL to avoid excessive system calls.
"""

import os
import subprocess
import sys
import time

from plmux.extensions import register_hook, register_status_item, ExtensionContext

_STATUS_PREFIX = "bat:"
_STYLE_CHARGING = "bold #85c751 on #75715e"
_STYLE_DISCHARGING_HIGH = "bold #85c751 on #75715e"
_STYLE_DISCHARGING_MID = "bold #fabd2f on #75715e"
_STYLE_DISCHARGING_LOW = "bold #f92672 on #75715e"
_STYLE_UNKNOWN = "dim white on #75715e"
_CACHE_TTL = 10.0

_cache: tuple[float, tuple[str, str] | None] = (0.0, None)


def _read_battery_linux() -> tuple[str, str] | None:
    bat_dir = None
    for entry in sorted(os.listdir("/sys/class/power_supply")):
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

    if status in ("Charging", "Not charging"):
        icon = "\u26A1"
        style = _STYLE_CHARGING
    elif status == "Full":
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
    return (f"{_STATUS_PREFIX}{label}", style)


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
        return (f"{_STATUS_PREFIX}{label}", style)

    return None


def _read_battery() -> tuple[str, str] | None:
    platform = sys.platform
    if platform == "linux":
        return _read_battery_linux()
    elif platform == "darwin":
        return _read_battery_macos()
    return None


def refresh_battery_status(ctx: ExtensionContext) -> None:
    global _cache
    now = time.monotonic()
    ts, cached_result = _cache
    if now - ts < _CACHE_TTL:
        if cached_result is not None:
            register_status_item(cached_result[0], cached_result[1])
        return

    result = _read_battery()
    _cache = (now, result)

    if result is not None:
        register_status_item(result[0], result[1])


register_hook("status_refresh", refresh_battery_status)
register_hook("app_started", refresh_battery_status)

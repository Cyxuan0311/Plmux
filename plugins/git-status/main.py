"""Git status plugin for plmux status bar.

Shows the current git branch and dirty/clean indicator in the status bar.
Refreshes on every status_refresh hook (throttled by registry to ~2s).
Results are cached with a 3-second TTL to avoid excessive subprocess calls.
"""

import os
import subprocess
import time

from plmux.extensions import register_hook, register_status_item, ExtensionContext

_STATUS_PREFIX = "git:"
_STATUS_STYLE_CLEAN = "bold #85c751 on #75715e"
_STATUS_STYLE_DIRTY = "bold #f92672 on #75715e"
_STATUS_STYLE_NOGIT = "dim white on #75715e"
_CACHE_TTL = 3.0

_cache: dict[str, tuple[float, tuple[str, str] | None]] = {}


def _run_git(args: list[str], cwd: str) -> str:
    try:
        r = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=1,
            cwd=cwd,
        )
        return r.stdout.strip()
    except Exception:
        return ""


def _compute_git_status(cwd: str) -> tuple[str, str] | None:
    is_git = _run_git(["rev-parse", "--is-inside-work-tree"], cwd)
    if is_git != "true":
        return None

    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)
    if not branch:
        return None

    porcelain = _run_git(["status", "--porcelain"], cwd)
    staged = 0
    unstaged = 0
    untracked = 0
    for line in porcelain.splitlines():
        if not line:
            continue
        x = line[0] if len(line) > 0 else " "
        y = line[1] if len(line) > 1 else " "
        if x in "MADRC":
            staged += 1
        if y in "MD":
            unstaged += 1
        if line.startswith("??"):
            untracked += 1

    parts = [branch]
    if staged:
        parts.append(f"+{staged}")
    if unstaged:
        parts.append(f"~{unstaged}")
    if untracked:
        parts.append(f"?{untracked}")

    label = " ".join(parts)
    dirty = staged > 0 or unstaged > 0 or untracked > 0
    style = _STATUS_STYLE_DIRTY if dirty else _STATUS_STYLE_CLEAN
    return (f"{_STATUS_PREFIX}{label}", style)


def refresh_git_status(ctx: ExtensionContext) -> None:
    cwd = os.getcwd()
    now = time.monotonic()

    cached = _cache.get(cwd)
    if cached is not None:
        ts, result = cached
        if now - ts < _CACHE_TTL:
            if result is not None:
                register_status_item(result[0], result[1])
            return

    result = _compute_git_status(cwd)
    _cache[cwd] = (now, result)

    if result is not None:
        register_status_item(result[0], result[1])


register_hook("status_refresh", refresh_git_status)
register_hook("app_started", refresh_git_status)

"""Shell detection and argv resolution."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import List, Optional, Sequence


def default_shell_argv() -> List[str]:
    if os.name == "nt":
        pwsh = shutil.which("pwsh.exe") or shutil.which("powershell.exe")
        if pwsh:
            return [pwsh, "-NoLogo"]
        cmd = shutil.which("cmd.exe")
        if cmd:
            return [cmd]
        return ["cmd.exe"]
    shell = _detect_parent_shell()
    if not shell:
        shell = os.environ.get("SHELL")
    if not shell:
        shell = shutil.which("bash") or "/bin/sh"
    return [shell]


def _detect_parent_shell() -> str | None:
    if os.name == "nt":
        return None
    try:
        ppid = os.getppid()
        with open(f"/proc/{ppid}/comm", "r") as f:
            comm = f.read().strip()
        if comm in ("zsh", "bash", "fish", "dash", "tcsh", "ksh", "sh"):
            exe = shutil.which(comm)
            if exe:
                return exe
    except (OSError, FileNotFoundError):
        pass
    return None


def resolve_shell_argv(cfg_shell: Optional[Sequence[str]]) -> List[str]:
    if cfg_shell:
        return list(cfg_shell)
    return default_shell_argv()


def ensure_interactive_shell(argv: List[str]) -> List[str]:
    if not argv:
        return argv
    exe = Path(argv[0]).name.lower()
    rest = list(argv[1:])

    _interactive_shells = ("bash", "zsh", "fish", "dash", "tcsh", "ksh")
    if any(exe.startswith(s) for s in _interactive_shells):
        if "-i" not in argv and "--norc" not in argv:
            return [argv[0], "-i"] + rest
        return list(argv)

    if exe.startswith("pwsh"):
        if (
            "-NoExit" not in argv
            and "-Command" not in argv
            and "-c" not in argv
            and "-File" not in argv
        ):
            return [argv[0], "-NoExit", "-Interactive"] + rest
        return list(argv)

    if exe.startswith("powershell"):
        if (
            "-NoExit" not in argv
            and "-Command" not in argv
            and "-c" not in argv
            and "-File" not in argv
        ):
            return [argv[0], "-NoExit", "-NoProfile"] + rest
        return list(argv)

    return list(argv)
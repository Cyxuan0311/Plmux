"""CLI command implementations (ls, lsw, kill-server, list_sessions)."""

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from plmux.daemon import connect_and_receive, is_server_alive, kill_server
from plmux.session.models import tree_from_json
from plmux.ui.geometry import count_panes, pane_indices

from plmux.config.schema import PlmuxConfig
from plmux.session.store import load_session, save_session
from plmux.state_bridge import spawn_server_subprocess
from plmux.daemon import ServerState, SessionHandle
from plmux.platform.shell import resolve_shell_argv

console = Console()


def new_session() -> None:
    cfg = PlmuxConfig()
    argv = resolve_shell_argv(cfg.shell)
    handle = SessionHandle(index=0, fd=-1, pid=-1, rows=24, cols=80, argv=argv)
    state = ServerState(tree=0, focus_pane=0, sessions=[handle], session_count=1, windows=[], current_window=0)
    spawn_server_subprocess(state)
    console.print(Panel(
        Text("Spawned detached plmux server", style="bold green"),
        title=" plmux ",
        border_style="green",
        padding=(0, 2),
    ))


def rename_window(index: int, name: str) -> None:
    cfg = PlmuxConfig()
    snap = load_session(cfg)
    if snap is None:
        console.print("[dim]no saved session to rename[/]")
        return
    meta = dict(snap.meta or {})
    wn = dict(meta.get("window_names") or {})
    wn[str(index)] = name
    meta["window_names"] = wn
    save_session(cfg, tree=snap.tree, focus_pane=snap.focus_pane, shell=snap.shell or cfg.shell, cwd=snap.cwd, extra_meta=meta)
    console.print(f"Renamed window [bold cyan]{index}[/] -> [bold yellow]{name}[/]")


def swap_panes(a: int, b: int) -> None:
    cfg = PlmuxConfig()
    snap = load_session(cfg)
    if snap is None:
        console.print("[dim]no saved session to operate on[/]")
        return

    def _swap_tree(t):
        if isinstance(t, int):
            if t == a:
                return b
            if t == b:
                return a
            return t
        d, r, A, B = t
        return (d, r, _swap_tree(A), _swap_tree(B))

    new_tree = _swap_tree(snap.tree)
    save_session(cfg, tree=new_tree, focus_pane=snap.focus_pane, shell=snap.shell or cfg.shell, cwd=snap.cwd, extra_meta=snap.meta)
    console.print(f"Swapped panes [bold cyan]{a}[/] <-> [bold cyan]{b}[/] in saved session")


def list_sessions() -> Dict[str, Any]:
    if not is_server_alive():
        return {"sessions": [], "windows": [], "current_window": 0}
    try:
        state, fds = asyncio.run(connect_and_receive())
        for fd in fds:
            try:
                os.close(fd)
            except OSError:
                pass
        result = []
        for s in state.sessions:
            result.append({
                "index": s.index,
                "pid": s.pid,
                "argv": s.argv,
                "rows": s.rows,
                "cols": s.cols,
            })
        return {
            "sessions": result,
            "windows": state.windows,
            "current_window": state.current_window,
        }
    except Exception:
        return {"sessions": [], "windows": [], "current_window": 0}


def cmd_list_sessions() -> None:
    data = list_sessions()
    sessions = data["sessions"]
    windows = data.get("windows", [])
    if not sessions:
        console.print(Panel(
            Text("No active plmux sessions", style="dim"),
            title=" plmux sessions ",
            border_style="dim",
            padding=(0, 2),
        ))
        return

    pane_count = len(sessions)
    win_count = len(windows) if windows else 1

    summary = Text()
    summary.append("1 session", style="bold white")
    summary.append("  |  ")
    summary.append(f"{win_count} window{'s' if win_count != 1 else ''}", style="bold cyan")
    summary.append("  |  ")
    summary.append(f"{pane_count} pane{'s' if pane_count != 1 else ''}", style="bold green")

    table = Table(
        show_header=True,
        header_style="bold",
        box=box.SIMPLE_HEAVY,
        border_style="dim",
        padding=(0, 2),
    )
    table.add_column("PANE", style="bold cyan", width=6)
    table.add_column("SHELL", style="white", min_width=10)
    table.add_column("PID", style="dim", width=8)
    table.add_column("SIZE", style="dim", width=10)

    for s in sessions:
        shell_name = s["argv"][0] if s["argv"] else "shell"
        shell_display = _shell_display(shell_name)
        pid_str = str(s["pid"])
        size_str = f"{s['cols']}x{s['rows']}"
        table.add_row(str(s["index"]), shell_display, pid_str, size_str)

    console.print()
    console.print(summary)
    console.print(table)
    console.print()


def cmd_list_windows(panes: bool = False) -> None:
    data = list_sessions()
    sessions = data["sessions"]
    windows = data.get("windows", [])
    current_window = data.get("current_window", 0)
    if not sessions:
        console.print(Panel(
            Text("No active plmux sessions", style="dim"),
            title=" plmux windows ",
            border_style="dim",
            padding=(0, 2),
        ))
        return

    if not windows:
        pane_count = len(sessions)
        marker = Text("*", style="bold green") if current_window == 0 else Text(" ", style="dim")
        header = Text.assemble(marker, " window ", Text("0", style="bold cyan"), f": {pane_count} pane{'s' if pane_count != 1 else ''}")
        console.print()
        console.print(header)
        if panes:
            _print_pane_list(sessions, range(len(sessions)))
        console.print()
        return

    console.print()
    for wi, w in enumerate(windows):
        tree = tree_from_json(w.get("tree", 0))
        pane_count = count_panes(tree)
        focus_pane = w.get("focus_pane", 0)

        if wi == current_window:
            marker = Text("*", style="bold green")
            win_label = Text(str(wi), style="bold cyan")
        else:
            marker = Text(" ", style="dim")
            win_label = Text(str(wi), style="cyan")

        header = Text.assemble(
            marker, " window ", win_label,
            f": {pane_count} pane{'s' if pane_count != 1 else ''}",
            "  ",
            Text(f"focus: pane {focus_pane}", style="dim"),
        )
        console.print(header)

        if panes:
            indices = pane_indices(tree)
            _print_pane_list(sessions, indices)
    console.print()


def _print_pane_list(sessions: list, indices) -> None:
    table = Table(
        show_header=False,
        box=None,
        padding=(0, 2),
        indent=4,
    )
    table.add_column(style="bold cyan", width=6)
    table.add_column(style="white", min_width=10)
    table.add_column(style="dim", width=8)
    table.add_column(style="dim", width=10)

    for pi in indices:
        if pi < len(sessions):
            s = sessions[pi]
            shell_name = s["argv"][0] if s["argv"] else "shell"
            shell_display = _shell_display(shell_name)
            pid_str = str(s["pid"])
            size_str = f"{s['cols']}x{s['rows']}"
            table.add_row(f"pane {pi}", shell_display, pid_str, size_str)

    console.print(table)


def _shell_display(shell_path: str) -> str:
    if "/" in shell_path:
        return shell_path.rsplit("/", 1)[-1]
    return shell_path


def cmd_kill_server() -> None:
    if kill_server():
        console.print(Panel(
            Text("Server killed", style="bold red"),
            title=" plmux ",
            border_style="red",
            padding=(0, 2),
        ))
    else:
        console.print(Panel(
            Text("No server running", style="dim"),
            title=" plmux ",
            border_style="dim",
            padding=(0, 2),
        ))

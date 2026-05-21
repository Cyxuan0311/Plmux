"""Nvim-style ':' command dispatch (extensible table)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from plmux.extensions.registry import ExtensionContext, emit_hook, get_plugin_commands
from plmux.workspace import PaneWorkspace


def _split_ws(line: str) -> List[str]:
    parts = line.strip().split()
    return [p for p in parts if p]


@dataclass
class CommandResult:
    message: Optional[str] = None
    quit: bool = False
    hard_quit: bool = False
    theme_changed: Optional[str] = None
    show_help: bool = False
    show_theme_list: bool = False
    show_session_list: bool = False
    show_plugin_list: bool = False
    show_layout_list: bool = False
    start_web_server: bool = False
    web_port: int = 9888
    stop_web_server: bool = False


def _cmd_exit(ws: PaneWorkspace, args: List[str]) -> CommandResult:
    return CommandResult(quit=True, hard_quit=True)


def _cmd_only(ws: PaneWorkspace, args: List[str]) -> CommandResult:
    ws.only_pane()
    return CommandResult("only this pane")


def _cmd_split(ws: PaneWorkspace, args: List[str]) -> CommandResult:
    ws.split("col")
    return CommandResult("split (stacked)")


def _cmd_vsplit(ws: PaneWorkspace, args: List[str]) -> CommandResult:
    ws.split("row")
    return CommandResult("vsplit (side-by-side)")


def _cmd_focus(ws: PaneWorkspace, args: List[str]) -> CommandResult:
    if not args:
        return CommandResult("usage: focus <n>")
    try:
        n = int(args[0])
    except ValueError:
        return CommandResult("focus: need integer")
    if 0 <= n < len(ws.sessions):
        ws.set_focus_pane(n)
        return CommandResult(f"focus -> {n}")
    return CommandResult("focus: out of range")


def _cmd_theme(ws: PaneWorkspace, args: List[str]) -> CommandResult:
    from plmux.ui.theme import list_themes, load_theme

    available = list_themes()
    if not args:
        return CommandResult(show_theme_list=True)
    name = args[0].lower()
    if name == "list":
        return CommandResult(show_theme_list=True)
    if name not in available:
        return CommandResult(f"unknown theme: {name}. available: {', '.join(available)}")
    ws.theme = load_theme(name)
    ws._mark()
    return CommandResult(f"theme -> {name}", theme_changed=name)


def _cmd_help(ws: PaneWorkspace, args: List[str]) -> CommandResult:
    return CommandResult(show_help=True)


def _cmd_ls(ws: PaneWorkspace, args: List[str]) -> CommandResult:
    return CommandResult(show_session_list=True)


def _cmd_plugin(ws: PaneWorkspace, args: List[str]) -> CommandResult:
    return CommandResult(show_plugin_list=True)


def _cmd_layout(ws: PaneWorkspace, args: List[str]) -> CommandResult:
    if args:
        name = args[0]
        if ws.apply_layout_template(name):
            return CommandResult(message=f"Layout applied: {name}")
        return CommandResult(message=f"Unknown layout: {name}")
    return CommandResult(show_layout_list=True)


def _cmd_web(ws: PaneWorkspace, args: List[str]) -> CommandResult:
    port = 9888
    if args:
        try:
            port = int(args[0])
        except ValueError:
            pass
    return CommandResult(start_web_server=True, web_port=port)


def _cmd_webstop(ws: PaneWorkspace, args: List[str]) -> CommandResult:
    return CommandResult(stop_web_server=True)


_ALIASES = {
    "sp": "split",
    "vsp": "vsplit",
    "vs": "vsplit",
}

_COMMANDS: Dict[str, Callable] = {
    "exit": _cmd_exit,
    "only": _cmd_only,
    "split": _cmd_split,
    "sp": _cmd_split,
    "vsplit": _cmd_vsplit,
    "vsp": _cmd_vsplit,
    "vs": _cmd_vsplit,
    "focus": _cmd_focus,
    "theme": _cmd_theme,
    "help": _cmd_help,
    "ls": _cmd_ls,
    "sessions": _cmd_ls,
    "plugin": _cmd_plugin,
    "plugins": _cmd_plugin,
    "layout": _cmd_layout,
    "web": _cmd_web,
    "webstop": _cmd_webstop,
}


def get_completions(prefix: str) -> List[str]:
    """Return command completions for the given prefix."""
    from plmux.ui.theme import list_themes

    all_commands = set(_COMMANDS.keys()) | set(get_plugin_commands().keys())

    has_trailing_space = prefix.endswith(" ")
    parts = prefix.strip().split()
    if not parts:
        return sorted(all_commands)

    if len(parts) == 1 and not has_trailing_space:
        word = parts[0].lower()
        return [c for c in sorted(all_commands) if c.startswith(word)]

    cmd = parts[0].lower()
    cmd = _ALIASES.get(cmd, cmd)

    if len(parts) == 1 and has_trailing_space:
        word = ""
    elif len(parts) >= 2:
        word = parts[-1].lower()
    else:
        word = ""

    if cmd == "theme" and (len(parts) == 2 or (len(parts) == 1 and has_trailing_space)):
        completions = ["list"]
        completions.extend(t for t in list_themes() if t.startswith(word))
        if word.startswith("l"):
            return completions
        return [t for t in list_themes() if t.startswith(word)]

    if cmd in ("plugin", "plugins") and (len(parts) == 2 or (len(parts) == 1 and has_trailing_space)):
        subcmds = ["list", "enable", "disable"]
        return [s for s in subcmds if s.startswith(word)]

    if cmd == "focus" and (len(parts) == 2 or (len(parts) == 1 and has_trailing_space)):
        return [str(i) for i in range(10) if str(i).startswith(word)]

    if cmd == "layout" and (len(parts) == 2 or (len(parts) == 1 and has_trailing_space)):
        from plmux.workspace import LAYOUT_TEMPLATES
        return [t.name for t in LAYOUT_TEMPLATES if t.name.startswith(word)]

    return []


def run_command_line(ws: PaneWorkspace, line: str) -> CommandResult:
    parts = _split_ws(line)
    if not parts:
        return CommandResult()
    cmd = parts[0].lower()
    cmd = _ALIASES.get(cmd, cmd)
    args = parts[1:]

    handler = _COMMANDS.get(cmd)
    if handler is not None:
        emit_hook("command_executed", ExtensionContext(hook_name="command_executed", command=cmd))
        return handler(ws, args)

    plugin_cmds = get_plugin_commands()
    plugin_handler = plugin_cmds.get(cmd)
    if plugin_handler is not None:
        emit_hook("command_executed", ExtensionContext(hook_name="command_executed", command=cmd))
        try:
            return plugin_handler(ws, args)
        except Exception as exc:
            return CommandResult(f"plugin command error: {exc}")

    emit_hook("command_unknown", ExtensionContext(hook_name="command_unknown", command=cmd))
    return CommandResult(f"unknown command: {cmd}")
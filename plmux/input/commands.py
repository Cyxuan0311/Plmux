"""Nvim-style ':' command dispatch (extensible table)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from plmux.extensions.registry import ExtensionContext, emit_hook, get_plugin_commands
from plmux.workspace import TmuxServer


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
    reload_config: bool = False
    plugin_overlay: Optional[str] = None
    toggle_broadcast: Optional[bool] = None
    toggle_clock_mode: Optional[bool] = None
    toggle_rect_mode: Optional[bool] = None
    pet_mode: Optional[str] = None
    rename_window: Optional[str] = None
    rename_session: Optional[str] = None
    switch_session: Optional[int] = None
    new_session_name: Optional[str] = None
    kill_session_idx: Optional[int] = None
    remote_command: Optional[dict] = None


def _cmd_exit(ws: TmuxServer, args: List[str]) -> CommandResult:
    return CommandResult(quit=True, hard_quit=True)


def _cmd_only(ws: TmuxServer, args: List[str]) -> CommandResult:
    ws.only_pane()
    return CommandResult("only this pane", remote_command={"action": "only_pane"})


def _cmd_split(ws: TmuxServer, args: List[str]) -> CommandResult:
    ws.split("col")
    return CommandResult("split (stacked)", remote_command={"action": "split", "direction": "col"})


def _cmd_vsplit(ws: TmuxServer, args: List[str]) -> CommandResult:
    ws.split("row")
    return CommandResult("vsplit (side-by-side)", remote_command={"action": "split", "direction": "row"})


def _cmd_focus(ws: TmuxServer, args: List[str]) -> CommandResult:
    if not args:
        return CommandResult("usage: focus <n>")
    try:
        n = int(args[0])
    except ValueError:
        return CommandResult("focus: need integer")
    if 0 <= n < len(ws._window().panes):
        ws.set_focus_pane(n)
        return CommandResult(f"focus -> {n}", remote_command={"action": "set_focus_pane", "index": n})
    return CommandResult("focus: out of range")


def _cmd_theme(ws: TmuxServer, args: List[str]) -> CommandResult:
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


def _cmd_help(ws: TmuxServer, args: List[str]) -> CommandResult:
    return CommandResult(show_help=True)


def _cmd_ls(ws: TmuxServer, args: List[str]) -> CommandResult:
    return CommandResult(show_session_list=True)


def _cmd_plugin(ws: TmuxServer, args: List[str]) -> CommandResult:
    return CommandResult(show_plugin_list=True)


def _cmd_layout(ws: TmuxServer, args: List[str]) -> CommandResult:
    if args:
        name = args[0]
        if ws.apply_layout_template(name):
            return CommandResult(message=f"Layout applied: {name}", remote_command={"action": "apply_layout_template", "name": name})
        return CommandResult(message=f"Unknown layout: {name}")
    return CommandResult(show_layout_list=True)


def _cmd_web(ws: TmuxServer, args: List[str]) -> CommandResult:
    port = 9888
    if args:
        try:
            port = int(args[0])
        except ValueError:
            pass
    return CommandResult(start_web_server=True, web_port=port)


def _cmd_webstop(ws: TmuxServer, args: List[str]) -> CommandResult:
    return CommandResult(stop_web_server=True)


def _cmd_reload(ws: TmuxServer, args: List[str]) -> CommandResult:
    return CommandResult(reload_config=True)


def _cmd_sync(ws: TmuxServer, args: List[str]) -> CommandResult:
    if not args:
        return CommandResult(toggle_broadcast=True)
    val = args[0].lower()
    if val in ("on", "yes", "1", "true"):
        return CommandResult(toggle_broadcast=True, message="synchronize-panes on")
    if val in ("off", "no", "0", "false"):
        return CommandResult(toggle_broadcast=False, message="synchronize-panes off")
    return CommandResult("usage: sync [on|off]")


def _cmd_rotate(ws: TmuxServer, args: List[str]) -> CommandResult:
    direction = "up"
    if args:
        d = args[0].lower()
        if d in ("down", "d"):
            direction = "down"
        elif d in ("up", "u"):
            direction = "up"
        else:
            return CommandResult("usage: rotate [up|down]")
    ws.rotate_panes(direction)
    return CommandResult(f"rotate-window {direction}", remote_command={"action": "rotate_panes", "direction": direction})


def _cmd_clock_mode(ws: TmuxServer, args: List[str]) -> CommandResult:
    return CommandResult(toggle_clock_mode=True)


def _cmd_pet(ws: TmuxServer, args: List[str]) -> CommandResult:
    from plmux.ui.pet_animation import get_pet_names
    if not args:
        return CommandResult(pet_mode="cat")
    pet_type = args[0].lower()
    if pet_type == "off":
        return CommandResult(pet_mode="off")
    if pet_type == "list":
        return CommandResult(message="pets: " + ", ".join(get_pet_names()))
    if pet_type not in get_pet_names():
        return CommandResult(message=f"unknown pet: {pet_type}. available: " + ", ".join(get_pet_names()))
    return CommandResult(pet_mode=pet_type)


def _cmd_rectangle_toggle(ws: TmuxServer, args: List[str]) -> CommandResult:
    return CommandResult(toggle_rect_mode=True)


def _cmd_rename_window(ws: TmuxServer, args: List[str]) -> CommandResult:
    name = " ".join(args).strip()
    if not name:
        return CommandResult(message="usage: rename-window <name>")
    return CommandResult(rename_window=name)


def _cmd_rename_session(ws: TmuxServer, args: List[str]) -> CommandResult:
    name = " ".join(args).strip()
    if not name:
        return CommandResult(message="usage: rename-session <name>")
    return CommandResult(rename_session=name)


def _cmd_new_session(ws: TmuxServer, args: List[str]) -> CommandResult:
    name = " ".join(args).strip()
    return CommandResult(new_session_name=name or "")


def _cmd_kill_session(ws: TmuxServer, args: List[str]) -> CommandResult:
    if args:
        try:
            idx = int(args[0])
            return CommandResult(kill_session_idx=idx)
        except ValueError:
            found = ws.find_session(args[0])
            if found >= 0:
                return CommandResult(kill_session_idx=found)
            return CommandResult(message=f"session not found: {args[0]}")
    return CommandResult(kill_session_idx=None)


def _cmd_switch_session(ws: TmuxServer, args: List[str]) -> CommandResult:
    if not args:
        return CommandResult(show_session_list=True)
    try:
        idx = int(args[0])
        return CommandResult(switch_session=idx)
    except ValueError:
        found = ws.find_session(args[0])
        if found >= 0:
            return CommandResult(switch_session=found)
        return CommandResult(message=f"session not found: {args[0]}")


def _cmd_next_session(ws: TmuxServer, args: List[str]) -> CommandResult:
    ws.next_session()
    return CommandResult(message=f"session -> {ws.session_name}", remote_command={"action": "next_session"})


def _cmd_prev_session(ws: TmuxServer, args: List[str]) -> CommandResult:
    ws.prev_session()
    return CommandResult(message=f"session -> {ws.session_name}", remote_command={"action": "prev_session"})


_ALIASES = {
    "sp": "split",
    "vsp": "vsplit",
    "vs": "vsplit",
    "synchronize-panes": "sync",
    "rotate-window": "rotate",
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
    "reload": _cmd_reload,
    "source": _cmd_reload,
    "sync": _cmd_sync,
    "synchronize-panes": _cmd_sync,
    "rotate": _cmd_rotate,
    "rotate-window": _cmd_rotate,
    "clock-mode": _cmd_clock_mode,
    "pet": _cmd_pet,
    "rectangle-toggle": _cmd_rectangle_toggle,
    "rename-window": _cmd_rename_window,
    "renamew": _cmd_rename_window,
    "rename-session": _cmd_rename_session,
    "renames": _cmd_rename_session,
    "new-session": _cmd_new_session,
    "new": _cmd_new_session,
    "kill-session": _cmd_kill_session,
    "kills": _cmd_kill_session,
    "switch-session": _cmd_switch_session,
    "switchs": _cmd_switch_session,
    "next-session": _cmd_next_session,
    "nexts": _cmd_next_session,
    "prev-session": _cmd_prev_session,
    "prevs": _cmd_prev_session,
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

    if cmd in ("sync", "synchronize-panes") and (len(parts) == 2 or (len(parts) == 1 and has_trailing_space)):
        return [s for s in ("on", "off") if s.startswith(word)]

    if cmd in ("rotate", "rotate-window") and (len(parts) == 2 or (len(parts) == 1 and has_trailing_space)):
        return [s for s in ("up", "down") if s.startswith(word)]

    if cmd == "pet" and (len(parts) == 2 or (len(parts) == 1 and has_trailing_space)):
        from plmux.ui.pet_animation import get_pet_names
        pet_opts = list(get_pet_names()) + ["off", "list"]
        return [s for s in pet_opts if s.startswith(word)]

    if cmd in ("switch-session", "switchs", "kill-session", "kills") and (len(parts) == 2 or (len(parts) == 1 and has_trailing_space)):
        return [str(i) for i in range(10) if str(i).startswith(word)]

    return []


def run_command_line(ws: TmuxServer, line: str) -> CommandResult:
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

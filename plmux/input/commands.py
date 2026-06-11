"""Nvim-style ':' command dispatch (extensible table)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from plmux.config.schema import KeysConfig
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
    show_memory: bool = False
    show_theme_list: bool = False
    show_session_list: bool = False
    show_statusbar_style: bool = False
    show_pane_border_style: bool = False
    show_plugin_list: bool = False
    show_layout_list: bool = False
    show_web_token: bool = False
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
    set_option: Optional[dict] = None
    show_options: bool = False


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


def _cmd_memory(ws: TmuxServer, args: List[str]) -> CommandResult:
    return CommandResult(show_memory=True)


def _cmd_ls(ws: TmuxServer, args: List[str]) -> CommandResult:
    return CommandResult(show_session_list=True)


def _cmd_statusbar(ws: TmuxServer, args: List[str]) -> CommandResult:
    return CommandResult(show_statusbar_style=True)


def _cmd_paneborder(ws: TmuxServer, args: List[str]) -> CommandResult:
    return CommandResult(show_pane_border_style=True)


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


def _cmd_web_token(ws: TmuxServer, args: List[str]) -> CommandResult:
    return CommandResult(show_web_token=True)


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


def _cmd_kill_pane(ws: TmuxServer, args: List[str]) -> CommandResult:
    if args:
        try:
            idx = int(args[0])
        except ValueError:
            return CommandResult("kill-pane: need integer index")
    else:
        idx = ws.focus_pane
    win = ws._window()
    if idx < 0 or idx >= len(win.panes):
        return CommandResult(f"kill-pane: index {idx} out of range")
    if len(win.panes) <= 1:
        return CommandResult(quit=True, hard_quit=True)
    ws.remove_pane(idx)
    return CommandResult(f"kill-pane {idx}", remote_command={"action": "kill_pane", "pane_index": idx})


def _cmd_swap_pane(ws: TmuxServer, args: List[str]) -> CommandResult:
    direction = "up"
    if args:
        d = args[0].lower()
        if d in ("up", "u", "left", "l"):
            direction = "up"
        elif d in ("down", "d", "right", "r"):
            direction = "down"
        else:
            return CommandResult("usage: swap-pane [up|down]")
    ws.swap_pane(direction)
    return CommandResult(f"swap-pane {direction}", remote_command={"action": "swap_pane", "direction": direction})


def _cmd_break_pane(ws: TmuxServer, args: List[str]) -> CommandResult:
    win = ws._window()
    if len(win.panes) <= 1:
        return CommandResult("break-pane: only one pane in window")
    pane_idx = ws.focus_pane
    ws.break_pane(pane_idx)
    return CommandResult("break-pane -> new window", remote_command={"action": "break_pane", "pane_index": pane_idx})


def _cmd_join_pane(ws: TmuxServer, args: List[str]) -> CommandResult:
    direction = "row"
    if args:
        d = args[0].lower()
        if d in ("vertical", "v", "col", "stacked", "s"):
            direction = "col"
        elif d in ("horizontal", "h", "row", "side", "side-by-side"):
            direction = "row"
        else:
            return CommandResult("usage: join-pane [horizontal|vertical]")
    ws.join_pane(direction)
    return CommandResult(f"join-pane {direction}", remote_command={"action": "join_pane", "direction": direction})


def _cmd_respawn_pane(ws: TmuxServer, args: List[str]) -> CommandResult:
    pane_idx = ws.focus_pane
    if args:
        try:
            pane_idx = int(args[0])
        except ValueError:
            return CommandResult("respawn-pane: need integer index")
    ws.respawn_pane(pane_idx)
    return CommandResult(f"respawn-pane {pane_idx}", remote_command={"action": "respawn_pane", "pane_index": pane_idx})


def _cmd_send_keys(ws: TmuxServer, args: List[str]) -> CommandResult:
    if not args:
        return CommandResult("usage: send-keys <text>")
    text = " ".join(args)
    ws.send_keys(text)
    return CommandResult(f"send-keys: sent {len(text)} chars", remote_command={"action": "send_keys", "text": text})


_SETTABLE_OPTIONS = {
    "remain-on-exit": ("ui", "remain_on_exit", bool),
    "status-position": ("ui", "status_position", str),
    "scrollback-lines": ("ui", "scrollback_lines", int),
    "min-pane-rows": ("ui", "min_pane_rows", int),
    "min-pane-cols": ("ui", "min_pane_cols", int),
    "synchronize-panes": ("_runtime", "synchronize_panes", bool),
    "prefix": ("keys", "prefix", str),
    "status-left-format": ("ui", "status_left_format", str),
    "status-right-format": ("ui", "status_right_format", str),
    "default-shell": ("shell", None, list),
}

_BINDABLE_ACTIONS = [
    ["split-vertical"],
    ["split-horizontal"],
    ["only-pane"],
    ["next-window"],
    ["prev-window"],
    ["new-window"],
    ["close-window"],
    ["copy-mode"],
    ["cycle-layout"],
    ["help"],
    ["detach"],
    ["focus-left"],
    ["focus-right"],
    ["focus-up"],
    ["focus-down"],
    ["resize-left"],
    ["resize-right"],
    ["resize-up"],
    ["resize-down"],
    ["zoom"],
    ["synchronize-panes"],
    ["rotate-window"],
    ["kill-pane"],
    ["swap-pane-up"],
    ["swap-pane-down"],
    ["break-pane"],
    ["clock-mode"],
    ["rectangle-toggle"],
    ["rename-window"],
    ["command-line"],
    ["next-session"],
    ["prev-session"],
    ["switch-session"],
    ["new-session"],
    ["rename-session"],
    ["last-window"],
    ["last-pane"],
    ["display-panes"],
]


def _parse_bool(val: str) -> bool:
    return val.lower() in ("on", "yes", "1", "true")


def _cmd_set_option(ws: TmuxServer, args: List[str]) -> CommandResult:
    if not args:
        return CommandResult("usage: set-option <name> <value>")
    name = args[0]
    spec = _SETTABLE_OPTIONS.get(name)
    if spec is None:
        return CommandResult(f"unknown option: {name}")
    section, attr, typ = spec
    if len(args) < 2:
        return CommandResult(f"usage: set-option {name} <value>")
    raw = " ".join(args[1:])
    if name == "synchronize-panes":
        val = _parse_bool(raw)
        return CommandResult(
            toggle_broadcast=val,
            message=f"set {name} -> {val}",
        )
    if name == "default-shell":
        ws.cfg.shell = raw.split()
        return CommandResult(f"set {name} -> {raw}")
    cfg_section = getattr(ws.cfg, section)
    if typ is bool:
        val = _parse_bool(raw)
    elif typ is int:
        try:
            val = int(raw)
        except ValueError:
            return CommandResult(f"invalid integer: {raw}")
    else:
        val = raw
    setattr(cfg_section, attr, val)
    return CommandResult(
        f"set {name} -> {val}",
        set_option={"section": section, "attr": attr, "value": val},
    )


def _cmd_show_options(ws: TmuxServer, args: List[str]) -> CommandResult:
    lines: list[str] = []
    for name, (section, attr, typ) in _SETTABLE_OPTIONS.items():
        if name == "synchronize-panes":
            lines.append(f"{name} = (runtime)")
            continue
        if name == "default-shell":
            shell = ws.cfg.shell
            lines.append(f"{name} = {' '.join(shell) if shell else '(default)'}")
            continue
        cfg_section = getattr(ws.cfg, section)
        val = getattr(cfg_section, attr, "(unset)")
        lines.append(f"{name} = {val}")
    return CommandResult(message="\n".join(lines), show_options=True)


def _cmd_bind_key(ws: TmuxServer, args: List[str]) -> CommandResult:
    if len(args) < 2:
        return CommandResult("usage: bind-key <key> <action>")
    key = args[0]
    action = args[1]
    bindings = ws.cfg.keys.bindings
    if action not in bindings:
        bindings[action] = []
    if key not in bindings[action]:
        bindings[action].append(key)
    return CommandResult(f"bound {key} -> {action}")


def _cmd_unbind_key(ws: TmuxServer, args: List[str]) -> CommandResult:
    if not args:
        return CommandResult("usage: unbind-key <key>")
    key = args[0]
    bindings = ws.cfg.keys.bindings
    found = False
    for action_keys in bindings.values():
        if key in action_keys:
            action_keys.remove(key)
            found = True
    if found:
        return CommandResult(f"unbound {key}")
    return CommandResult(f"key not bound: {key}")


def _cmd_display_panes(ws: TmuxServer, args: List[str]) -> CommandResult:
    return CommandResult(remote_command={"action": "display_panes"})


def _cmd_last_window(ws: TmuxServer, args: List[str]) -> CommandResult:
    ws.last_window()
    return CommandResult(f"last-window -> {ws._session().current_window}", remote_command={"action": "last_window"})


def _cmd_last_pane(ws: TmuxServer, args: List[str]) -> CommandResult:
    ws.last_pane()
    return CommandResult(f"last-pane -> {ws.focus_pane}", remote_command={"action": "last_pane"})


def _cmd_set_buffer(ws: TmuxServer, args: List[str]) -> CommandResult:
    if not args:
        return CommandResult("usage: set-buffer <data>")
    data = " ".join(args)
    name = ws.buffers.set(data)
    return CommandResult(f"set-buffer -> {name} ({len(data)} bytes)")


def _cmd_show_buffer(ws: TmuxServer, args: List[str]) -> CommandResult:
    name = args[0] if args else None
    data = ws.buffers.paste(name)
    if data is None:
        return CommandResult("no buffer" + (f" '{name}'" if name else ""))
    preview = data[:200] + ("..." if len(data) > 200 else "")
    return CommandResult(message=preview)


def _cmd_list_buffers(ws: TmuxServer, args: List[str]) -> CommandResult:
    items = ws.buffers.list()
    if not items:
        return CommandResult(message="no buffers")
    lines = []
    for bname, size, created in items:
        import time as _time
        ts = _time.strftime("%H:%M:%S", _time.localtime(created))
        lines.append(f"{bname}  {size} bytes  {ts}")
    return CommandResult(message="\n".join(lines))


def _cmd_delete_buffer(ws: TmuxServer, args: List[str]) -> CommandResult:
    if not args:
        return CommandResult("usage: delete-buffer <name>")
    name = args[0]
    if ws.buffers.delete(name):
        return CommandResult(f"deleted buffer: {name}")
    return CommandResult(f"buffer not found: {name}")


def _cmd_save_buffer(ws: TmuxServer, args: List[str]) -> CommandResult:
    if len(args) < 2:
        return CommandResult("usage: save-buffer <name> <path>")
    name, path = args[0], args[1]
    if ws.buffers.save(name, path):
        return CommandResult(f"saved buffer {name} -> {path}")
    return CommandResult(f"failed to save buffer: {name}")


def _cmd_load_buffer(ws: TmuxServer, args: List[str]) -> CommandResult:
    if not args:
        return CommandResult("usage: load-buffer <path> [name]")
    path = args[0]
    name = args[1] if len(args) > 1 else None
    result = ws.buffers.load(path, name)
    if result is not None:
        return CommandResult(f"loaded buffer: {result}")
    return CommandResult(f"failed to load buffer from: {path}")


def _cmd_paste_buffer(ws: TmuxServer, args: List[str]) -> CommandResult:
    name = args[0] if args else None
    data = ws.buffers.paste(name)
    if data is None:
        return CommandResult("no buffer to paste")
    ws.send_keys(data)
    return CommandResult(f"pasted {len(data)} chars", remote_command={"action": "send_keys", "text": data})


def _cmd_set_environment(ws: TmuxServer, args: List[str]) -> CommandResult:
    if len(args) < 2:
        return CommandResult("usage: set-environment <key> <value>")
    key = args[0]
    value = " ".join(args[1:])
    ws.setenv(key, value)
    return CommandResult(f"setenv {key}={value}")


def _cmd_show_environment(ws: TmuxServer, args: List[str]) -> CommandResult:
    env = ws.showenv()
    if not env:
        return CommandResult(message="(no session environment)")
    lines = [f"{k}={v}" for k, v in sorted(env.items())]
    return CommandResult(message="\n".join(lines))


def _cmd_unset_environment(ws: TmuxServer, args: List[str]) -> CommandResult:
    if not args:
        return CommandResult("usage: unset-environment <key>")
    key = args[0]
    if ws.unsetenv(key):
        return CommandResult(f"unsetenv {key}")
    return CommandResult(f"environment variable not found: {key}")


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
    "kill-pane": _cmd_kill_pane,
    "killp": _cmd_kill_pane,
    "swap-pane": _cmd_swap_pane,
    "swapp": _cmd_swap_pane,
    "break-pane": _cmd_break_pane,
    "breakp": _cmd_break_pane,
    "join-pane": _cmd_join_pane,
    "joinp": _cmd_join_pane,
    "respawn-pane": _cmd_respawn_pane,
    "respawnp": _cmd_respawn_pane,
    "send-keys": _cmd_send_keys,
    "sendk": _cmd_send_keys,
    "set-option": _cmd_set_option,
    "set": _cmd_set_option,
    "show-options": _cmd_show_options,
    "show": _cmd_show_options,
    "bind-key": _cmd_bind_key,
    "bind": _cmd_bind_key,
    "unbind-key": _cmd_unbind_key,
    "unbind": _cmd_unbind_key,
    "display-panes": _cmd_display_panes,
    "displayp": _cmd_display_panes,
    "last-window": _cmd_last_window,
    "lastw": _cmd_last_window,
    "last-pane": _cmd_last_pane,
    "lastp": _cmd_last_pane,
    "set-buffer": _cmd_set_buffer,
    "setb": _cmd_set_buffer,
    "show-buffer": _cmd_show_buffer,
    "showb": _cmd_show_buffer,
    "list-buffers": _cmd_list_buffers,
    "lsb": _cmd_list_buffers,
    "delete-buffer": _cmd_delete_buffer,
    "deleteb": _cmd_delete_buffer,
    "save-buffer": _cmd_save_buffer,
    "saveb": _cmd_save_buffer,
    "load-buffer": _cmd_load_buffer,
    "loadb": _cmd_load_buffer,
    "paste-buffer": _cmd_paste_buffer,
    "pasteb": _cmd_paste_buffer,
    "set-environment": _cmd_set_environment,
    "setenv": _cmd_set_environment,
    "show-environment": _cmd_show_environment,
    "showenv": _cmd_show_environment,
    "unset-environment": _cmd_unset_environment,
    "unsetenv": _cmd_unset_environment,
    "theme": _cmd_theme,
    "help": _cmd_help,
    "memory": _cmd_memory,
    "mem": _cmd_memory,
    "ls": _cmd_ls,
    "sessions": _cmd_ls,
    "statusbar": _cmd_statusbar,
    "paneborder": _cmd_paneborder,
    "plugin": _cmd_plugin,
    "plugins": _cmd_plugin,
    "layout": _cmd_layout,
    "web": _cmd_web,
    "webstop": _cmd_webstop,
    "web-token": _cmd_web_token,
    "webtoken": _cmd_web_token,
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

    if cmd in ("set-option", "set") and (len(parts) == 2 or (len(parts) == 1 and has_trailing_space)):
        return [o for o in _SETTABLE_OPTIONS if o.startswith(word)]

    if cmd in ("bind-key", "bind") and (len(parts) >= 2 or (len(parts) == 1 and has_trailing_space)):
        if len(parts) == 2 and not has_trailing_space:
            return []
        if len(parts) == 2 and has_trailing_space or len(parts) >= 3:
            actions = [a[0] for a in _BINDABLE_ACTIONS]
            return [a for a in sorted(actions) if a.startswith(word)]
        return []

    if cmd in ("unbind-key", "unbind") and (len(parts) == 2 or (len(parts) == 1 and has_trailing_space)):
        all_keys = set()
        for action_keys in KeysConfig().bindings.values():
            all_keys.update(action_keys)
        return [k for k in sorted(all_keys) if k.startswith(word)]

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

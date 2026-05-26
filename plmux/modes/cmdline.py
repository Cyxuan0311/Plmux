"""Command-line mode handler: `:` command input."""

from __future__ import annotations

from plmux.config.loader import load_config, save_user_config
from plmux.extensions.registry import load_plugins, set_plugin_settings
from plmux.input.commands import get_completions, run_command_line
from plmux.modes import AppContext


def _common_prefix(strings: list[str]) -> str:
    if not strings:
        return ""
    prefix = strings[0]
    for s in strings[1:]:
        i = 0
        while i < min(len(prefix), len(s)) and prefix[i] == s[i]:
            i += 1
        prefix = prefix[:i]
    return prefix


def _apply_tab_completion(cmd_buffer: str) -> tuple[str, str]:
    completions = get_completions(cmd_buffer)
    if not completions:
        return cmd_buffer, ""

    if len(completions) == 1:
        parts = cmd_buffer.strip().split()
        if len(parts) <= 1:
            return completions[0] + " ", ""
        else:
            prefix = " ".join(parts[:-1])
            return prefix + " " + completions[0] + " ", ""

    common = _common_prefix(completions)
    parts = cmd_buffer.strip().split()
    current_word = parts[-1] if parts else ""

    if common and len(common) > len(current_word):
        if len(parts) <= 1:
            return common + " ", "  ".join(completions)
        else:
            prefix = " ".join(parts[:-1])
            return prefix + " " + common + " ", "  ".join(completions)

    return cmd_buffer, "  ".join(completions)


def handle_cmdline_mode(key, ctx: AppContext) -> None:
    if key.name == "KEY_ESCAPE":
        ctx.mode = "normal"
        ctx.cmd_buffer = ""
        ctx.cmd_history_pos = -1
        ctx.cmd_history_draft = ""
        ctx.completion_hints = ""
        ctx.dirty = True
    elif not key.is_sequence and str(key) == "\x04":
        pass
    elif key.name == "KEY_TAB":
        new_buffer, hints = _apply_tab_completion(ctx.cmd_buffer)
        ctx.cmd_buffer = new_buffer
        ctx.completion_hints = hints
        ctx.dirty = True
    elif key in ("\n", "\r") or key.name == "KEY_ENTER":
        cmd_text = ctx.cmd_buffer.strip()
        if cmd_text:
            if not ctx.cmd_history or ctx.cmd_history[-1] != cmd_text:
                ctx.cmd_history.append(cmd_text)
            if len(ctx.cmd_history) > 200:
                ctx.cmd_history = ctx.cmd_history[-200:]
        ctx.cmd_history_pos = -1
        ctx.cmd_history_draft = ""
        res = run_command_line(ctx.ws, ctx.cmd_buffer)
        ctx.cmd_buffer = ""
        ctx.completion_hints = ""
        ctx.mode = "normal"
        if res.quit:
            if res.hard_quit:
                ctx.hard_quit_requested = True
            ctx.running = False
        if res.theme_changed:
            ctx.cfg.theme = res.theme_changed
            save_user_config(ctx.cfg, None)
        if res.show_help:
            ctx.mode = "help"
            ctx.help_tab = 0
        if res.show_theme_list:
            ctx.mode = "theme_list"
            ctx.theme_list_cursor = 0
        if res.show_session_list:
            ctx.mode = "session_list"
            ctx.session_list_cursor = 0
        if res.show_statusbar_style:
            ctx.mode = "statusbar_style"
            ctx.statusbar_style_cursor = 0
        if res.show_pane_border_style:
            ctx.mode = "pane_border_style"
            ctx.pane_border_style_cursor = 0
        if res.show_plugin_list:
            ctx.mode = "plugin_list"
            ctx.plugin_list_cursor = 0
        if res.show_layout_list:
            ctx.mode = "layout_list"
            ctx.layout_list_cursor = 0
        if res.start_web_server:
            ctx._pending_web_port = res.web_port
        if res.stop_web_server:
            ctx._pending_web_stop = True
        if res.reload_config:
            _do_reload_config(ctx)
        if res.toggle_broadcast is not None:
            if res.toggle_broadcast and not ctx.broadcast_enabled:
                ctx.broadcast_enabled = True
            elif not res.toggle_broadcast and ctx.broadcast_enabled:
                ctx.broadcast_enabled = False
            elif res.toggle_broadcast and ctx.broadcast_enabled:
                ctx.broadcast_enabled = False
        if res.toggle_clock_mode:
            if ctx.clock_mode_pane is not None:
                ctx.clock_mode_pane = None
            else:
                ctx.clock_mode_pane = ctx.ws.focus_pane
        if res.pet_mode is not None:
            if res.pet_mode == "off":
                ctx.pet_mode_pane = None
                ctx.pet_type = ""
                ctx.pet_frame = 0
            else:
                ctx.pet_mode_pane = ctx.ws.focus_pane
                ctx.pet_type = res.pet_mode
                ctx.pet_frame = 0
        if res.toggle_rect_mode:
            if ctx.mode == "copy":
                ctx.copy_rect_mode = not ctx.copy_rect_mode
                if ctx.copy_rect_mode:
                    ctx.copy_line_mode = False
                    s = ctx.ws.active_session()
                    s.copy_line_mode = False
                    s.copy_rect_mode = True
                else:
                    s = ctx.ws.active_session()
                    s.copy_rect_mode = False
        if res.rename_window is not None:
            ctx.ws.rename_window(res.rename_window)
            if ctx.send_remote_command:
                ctx.send_remote_command({"action": "rename_window", "name": res.rename_window})
        if res.rename_session is not None:
            ctx.ws.rename_session(res.rename_session)
            if ctx.send_remote_command:
                ctx.send_remote_command({"action": "rename_session", "name": res.rename_session})
        if res.new_session_name is not None:
            ctx.ws.new_session(res.new_session_name)
            if ctx.send_remote_command:
                ctx.send_remote_command({"action": "new_session", "name": res.new_session_name})
        if res.kill_session_idx is not None:
            ctx.ws.kill_session(res.kill_session_idx)
            if ctx.send_remote_command:
                ctx.send_remote_command({"action": "kill_session", "index": res.kill_session_idx})
        if res.switch_session is not None:
            idx = res.switch_session
            if 0 <= idx < len(ctx.ws.sessions_list):
                ctx.ws.switch_session(idx)
                if ctx.send_remote_command:
                    ctx.send_remote_command({"action": "switch_session", "index": idx})
        if res.plugin_overlay:
            ctx.mode = res.plugin_overlay
            from plmux.extensions.registry import get_plugin_mode_handler
            handler = get_plugin_mode_handler(res.plugin_overlay)
            if handler and hasattr(handler, "_on_enter"):
                handler._on_enter(ctx)
        if res.show_options:
            ctx.cmd_buffer = res.message or ""
            ctx.mode = "cmdline"
        if res.remote_command:
            cmd = res.remote_command
            if cmd.get("action") == "display_panes":
                import time as _time
                ctx.display_panes_active = True
                ctx.display_panes_until = _time.monotonic() + 3.0
                ctx.dirty = True
            elif ctx.send_remote_command:
                if cmd.get("action") == "split" and "rows" not in cmd:
                    cmd["rows"] = ctx.content_rows
                    cmd["cols"] = ctx.content_cols
                ctx.send_remote_command(cmd)
        ctx.dirty = True
    elif key.name == "KEY_UP":
        if ctx.cmd_history:
            if ctx.cmd_history_pos == -1:
                ctx.cmd_history_draft = ctx.cmd_buffer
                ctx.cmd_history_pos = len(ctx.cmd_history) - 1
            elif ctx.cmd_history_pos > 0:
                ctx.cmd_history_pos -= 1
            ctx.cmd_buffer = ctx.cmd_history[ctx.cmd_history_pos]
            ctx.completion_hints = ""
            ctx.dirty = True
    elif key.name == "KEY_DOWN":
        if ctx.cmd_history_pos >= 0:
            if ctx.cmd_history_pos < len(ctx.cmd_history) - 1:
                ctx.cmd_history_pos += 1
                ctx.cmd_buffer = ctx.cmd_history[ctx.cmd_history_pos]
            else:
                ctx.cmd_history_pos = -1
                ctx.cmd_buffer = ctx.cmd_history_draft
            ctx.completion_hints = ""
            ctx.dirty = True
    elif key.name in ("KEY_BACKSPACE", "KEY_DELETE"):
        ctx.cmd_buffer = ctx.cmd_buffer[:-1]
        ctx.completion_hints = ""
        ctx.dirty = True
    else:
        if not key.is_sequence:
            ctx.cmd_buffer += str(key)
            ctx.completion_hints = ""
            ctx.dirty = True


def _do_reload_config(ctx: AppContext) -> None:
    try:
        new_cfg = load_config()
        old_enabled = set(ctx.cfg.extensions.enabled)
        ctx.cfg = new_cfg
        ctx.prefix_key = _parse_prefix_key(new_cfg.keys.prefix)
        trig_type, trig_val = _parse_cmdline_trigger(new_cfg.keys.command_line)
        ctx.cmdline_trigger_type = trig_type
        ctx.cmdline_trigger_val = trig_val
        from plmux.ui.theme import load_theme
        ctx.theme = load_theme(new_cfg.theme)
        ctx.ws.theme = ctx.theme
        new_enabled = set(new_cfg.extensions.enabled)
        to_load = new_enabled - old_enabled
        if to_load:
            set_plugin_settings(new_cfg.extensions.plugin_settings)
            load_plugins(list(to_load), new_cfg.extensions.search_paths)
    except Exception:
        pass


def _parse_prefix_key(spec: str) -> str:
    s = (spec or "ctrl+b").lower().strip()
    if s in ("ctrl+b", "c-b", "^b"):
        return chr(2)
    if s in ("ctrl+a", "c-a", "^a"):
        return chr(1)
    return chr(2)


def _parse_cmdline_trigger(spec: str) -> tuple[str, str]:
    s = (spec or ":").strip()
    low = s.lower()
    if low in ("ctrl+shift+:", "c-s-:", "ctrl+shift+;", "c-s-;"):
        return ("chord", "ctrl+shift+;")
    return ("char", s[:1])
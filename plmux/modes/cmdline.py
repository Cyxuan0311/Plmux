"""Command-line mode handler: `:` command input."""

from __future__ import annotations

from plmux.config.loader import save_user_config
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
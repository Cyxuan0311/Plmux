"""Memory overlay mode handler."""

from __future__ import annotations

from plmux.modes import AppContext


def handle_memory_mode(key, ctx: AppContext) -> None:
    name = getattr(key, "name", "")
    ch = str(key) if not key.is_sequence else ""

    if name == "KEY_ESCAPE" or ch == "q":
        ctx.mode = "normal"
        ctx.memory_cursor = 0
        ctx.dirty = True
        return

    max_lines = _count_lines(ctx)

    if name in ("KEY_UP",) or ch == "k":
        if ctx.memory_cursor > 0:
            ctx.memory_cursor -= 1
        ctx.dirty = True
        return

    if name in ("KEY_DOWN",) or ch == "j":
        if ctx.memory_cursor < max_lines - 1:
            ctx.memory_cursor += 1
        ctx.dirty = True
        return

    if name in ("KEY_HOME",) or ch == "g":
        ctx.memory_cursor = 0
        ctx.dirty = True
        return

    if name in ("KEY_END",) or ch == "G":
        ctx.memory_cursor = max_lines - 1 if max_lines > 0 else 0
        ctx.dirty = True
        return

    if name in ("KEY_PPAGE",):
        ctx.memory_cursor = max(0, ctx.memory_cursor - 10)
        ctx.dirty = True
        return

    if name in ("KEY_NPAGE",):
        ctx.memory_cursor = min(max_lines - 1, ctx.memory_cursor + 10)
        ctx.dirty = True
        return

    ctx.dirty = True


def _count_lines(ctx: AppContext) -> int:
    """Count total selectable lines in the memory tree."""
    count = 1  # plmux header is one line
    try:
        for sess in ctx.ws.sessions_list:
            count += 1  # session line
            for win in getattr(sess, "windows", []):
                count += 1  # window line
                count += len(getattr(win, "panes", []))  # pane lines
    except Exception:
        pass
    return count

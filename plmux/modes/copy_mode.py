"""Copy mode handler: text selection and yank."""

from __future__ import annotations

from plmux.modes import AppContext
from plmux.platform.clipboard import copy_to_clipboard as _copy_to_clipboard


def _extract_selected_text_from_session(s, a: tuple[int, int], b: tuple[int, int]) -> str:
    if a is None or b is None:
        return ""
    ay, ax = a
    by, bx = b
    if (ay, ax) > (by, bx):
        ay, ax, by, bx = by, bx, ay, ax
    lines: list[str] = []
    with s._screen_lock:
        for y in range(max(0, ay), min(s.rows, by) + 1):
            line = s.screen.buffer.get(y, {})
            if ay == by:
                start_x = max(0, min(s.cols - 1, ax))
                end_x = max(0, min(s.cols - 1, bx))
            elif y == ay:
                start_x = max(0, min(s.cols - 1, ax))
                end_x = s.cols - 1
            elif y == by:
                start_x = 0
                end_x = max(0, min(s.cols - 1, bx))
            else:
                start_x = 0
                end_x = s.cols - 1
            row_chars: list[str] = []
            for x in range(start_x, end_x + 1):
                ch = line.get(x)
                if ch is None:
                    glyph = " "
                elif isinstance(ch, dict):
                    glyph = ch.get("data", " ")
                elif hasattr(ch, "data"):
                    glyph = ch.data
                else:
                    glyph = str(ch)
                row_chars.append(glyph)
            lines.append("".join(row_chars).rstrip())
    return "\n".join(lines)


def _clamp(y: int, x: int, rows: int, cols: int) -> tuple[int, int]:
    y = max(0, min(rows - 1, y))
    x = max(0, min(cols - 1, x))
    return (y, x)


def handle_copy_mode(key, ctx: AppContext) -> None:
    if ctx.copy_pane is not None and 0 <= ctx.copy_pane < len(ctx.ws.sessions):
        s = ctx.ws.sessions[ctx.copy_pane]
    else:
        s = ctx.ws.active_session()

    def clamp(y, x):
        return _clamp(y, x, s.rows, s.cols)

    if (key.name == "KEY_ESCAPE") or (not key.is_sequence and str(key) in ("q",)) or key == ctx.prefix_key:
        _exit_copy_mode(ctx, s)
        return

    if key.name == "KEY_PPAGE":
        y, x = ctx.copy_cursor or (s.screen.cursor.y, s.screen.cursor.x)
        ctx.copy_cursor = clamp(y - max(1, s.rows - 1), x)
    elif key.name == "KEY_NPAGE":
        y, x = ctx.copy_cursor or (s.screen.cursor.y, s.screen.cursor.x)
        ctx.copy_cursor = clamp(y + max(1, s.rows - 1), x)
    elif key.name == "KEY_HOME":
        y, x = ctx.copy_cursor or (s.screen.cursor.y, s.screen.cursor.x)
        ctx.copy_cursor = (y, 0)
    elif key.name == "KEY_END":
        y, x = ctx.copy_cursor or (s.screen.cursor.y, s.screen.cursor.x)
        ctx.copy_cursor = (y, s.cols - 1)
    elif not key.is_sequence and str(key) == "V":
        ctx.copy_line_mode = not ctx.copy_line_mode
        setattr(s, "_copy_line_mode", ctx.copy_line_mode)
        ctx.dirty = True
        return

    if key.name == "KEY_UP":
        y, x = ctx.copy_cursor or (s.screen.cursor.y, s.screen.cursor.x)
        ctx.copy_cursor = clamp(y - 1, x)
    elif key.name == "KEY_DOWN":
        y, x = ctx.copy_cursor or (s.screen.cursor.y, s.screen.cursor.x)
        ctx.copy_cursor = clamp(y + 1, x)
    elif key.name == "KEY_LEFT":
        y, x = ctx.copy_cursor or (s.screen.cursor.y, s.screen.cursor.x)
        ctx.copy_cursor = clamp(y, x - 1)
    elif key.name == "KEY_RIGHT":
        y, x = ctx.copy_cursor or (s.screen.cursor.y, s.screen.cursor.x)
        ctx.copy_cursor = clamp(y, x + 1)
    elif not key.is_sequence and str(key) == "y":
        if ctx.copy_anchor is not None and ctx.copy_cursor is not None:
            text = _extract_selected_text_from_session(s, ctx.copy_anchor, ctx.copy_cursor)
            _copy_to_clipboard(text)
        _exit_copy_mode(ctx, s)
        return

    if ctx.copy_anchor is not None and ctx.copy_cursor is not None:
        setattr(s, "_copy_sel_start", ctx.copy_anchor)
        setattr(s, "_copy_sel_end", ctx.copy_cursor)
        setattr(s, "_copy_cursor_pos", ctx.copy_cursor)
    ctx.dirty = True


def _exit_copy_mode(ctx: AppContext, s) -> None:
    ctx.mode = "normal"
    ctx.copy_anchor = None
    ctx.copy_cursor = None
    ctx.copy_pane = None
    try:
        delattr(s, "_copy_sel_start")
        delattr(s, "_copy_sel_end")
        delattr(s, "_copy_cursor_pos")
    except Exception:
        pass
    s._line_cache.clear()
    s._last_cursor_y = -1
    s._last_cursor_x = -1
    ctx.dirty = True
"""Copy mode handler: scrollback, text selection, search, and yank."""

from __future__ import annotations

import re

from plmux.modes import AppContext
from plmux.platform.clipboard import copy_to_clipboard as _copy_to_clipboard


def _extract_selected_text(s, a: tuple[int, int], b: tuple[int, int], scroll_offset: int = 0, rect_mode: bool = False) -> str:
    if a is None or b is None:
        return ""
    ay, ax = a
    by, bx = b
    if (ay, ax) > (by, bx):
        ay, ax, by, bx = by, bx, ay, ax
    sb_len = s.scrollback_len
    logical_ay = sb_len - scroll_offset + ay
    logical_by = sb_len - scroll_offset + by

    if rect_mode:
        col_start = min(ax, bx)
        col_end = max(ax, bx)
        lines: list[str] = []
        for logical_y in range(max(0, logical_ay), min(s.total_lines(), logical_by + 1)):
            plain = s.get_line_plain_text(logical_y)
            start_x = max(0, min(len(plain), col_start))
            end_x = max(0, min(len(plain), col_end + 1))
            lines.append(plain[start_x:end_x])
        return "\n".join(lines)

    lines = []
    for logical_y in range(max(0, logical_ay), min(s.total_lines(), logical_by + 1)):
        plain = s.get_line_plain_text(logical_y)
        if logical_y == logical_ay and logical_y == logical_by:
            start_x = max(0, min(len(plain), ax))
            end_x = max(0, min(len(plain), bx + 1))
            lines.append(plain[start_x:end_x])
        elif logical_y == logical_ay:
            start_x = max(0, min(len(plain), ax))
            lines.append(plain[start_x:])
        elif logical_y == logical_by:
            end_x = max(0, min(len(plain), bx + 1))
            lines.append(plain[:end_x])
        else:
            lines.append(plain)
    return "\n".join(lines)


def _do_search(s, query: str, direction: str, start_y: int, start_x: int) -> list[tuple[int, int, int]]:
    if not query:
        return []
    matches: list[tuple[int, int, int]] = []
    total = s.total_lines()
    try:
        pattern = re.compile(re.escape(query), re.IGNORECASE)
    except re.error:
        return []
    for logical_y in range(total):
        plain = s.get_line_plain_text(logical_y)
        for m in pattern.finditer(plain):
            matches.append((logical_y, m.start(), m.end() - m.start()))
    return matches


def _jump_to_match(ctx: AppContext, s, matches: list[tuple[int, int, int]], idx: int) -> None:
    if not matches or idx < 0 or idx >= len(matches):
        return
    my, mx, mlen = matches[idx]
    sb_len = s.scrollback_len
    offset = max(0, sb_len - my)
    offset = min(offset, sb_len)
    if my < sb_len - offset or my >= sb_len - offset + s.rows:
        offset = max(0, sb_len - my)
        offset = min(offset, sb_len)
    ctx.copy_scroll_offset = offset
    vis_y = my - (sb_len - offset)
    ctx.copy_cursor = (vis_y, mx)
    ctx.copy_search_match_idx = idx


def _ensure_cursor_visible(ctx: AppContext, s) -> None:
    sb_len = s.scrollback_len
    if ctx.copy_cursor is None:
        return
    cy, cx = ctx.copy_cursor
    if cy < 0:
        new_offset = ctx.copy_scroll_offset - cy
        ctx.copy_scroll_offset = max(0, min(new_offset, sb_len))
        ctx.copy_cursor = (0, cx)
    elif cy >= s.rows:
        shift = cy - s.rows + 1
        new_offset = ctx.copy_scroll_offset + shift
        ctx.copy_scroll_offset = min(new_offset, sb_len)
        ctx.copy_cursor = (s.rows - 1, cx)


def handle_copy_mode(key, ctx: AppContext) -> None:
    if ctx.copy_pane is not None:
        win = ctx.ws._window()
        if 0 <= ctx.copy_pane < len(win.panes):
            s = win.panes[ctx.copy_pane]
        else:
            s = ctx.ws.active_session()
    else:
        s = ctx.ws.active_session()

    if ctx.copy_search_active:
        _handle_search_input(key, ctx, s)
        return

    if (key.name == "KEY_ESCAPE") or (not key.is_sequence and str(key) in ("q",)) or key == ctx.prefix_key:
        _exit_copy_mode(ctx, s)
        return

    key_char = "" if key.is_sequence else str(key)

    if key.name == "KEY_PPAGE":
        ctx.copy_scroll_offset = min(ctx.copy_scroll_offset + s.rows - 1, s.scrollback_len)
        if ctx.copy_cursor:
            cy, cx = ctx.copy_cursor
            ctx.copy_cursor = (max(0, cy - (s.rows - 1)), cx)
        ctx.dirty = True
        _sync_attrs(ctx, s)
        return

    if key.name == "KEY_NPAGE":
        ctx.copy_scroll_offset = max(ctx.copy_scroll_offset - (s.rows - 1), 0)
        if ctx.copy_cursor:
            cy, cx = ctx.copy_cursor
            ctx.copy_cursor = (min(s.rows - 1, cy + (s.rows - 1)), cx)
        ctx.dirty = True
        _sync_attrs(ctx, s)
        return

    if key.name == "KEY_UP" or key_char == "k":
        if ctx.copy_cursor:
            cy, cx = ctx.copy_cursor
            if cy > 0:
                ctx.copy_cursor = (cy - 1, cx)
            elif ctx.copy_scroll_offset < s.scrollback_len:
                ctx.copy_scroll_offset += 1
        ctx.dirty = True
        _sync_attrs(ctx, s)
        return

    if key.name == "KEY_DOWN" or key_char == "j":
        if ctx.copy_cursor:
            cy, cx = ctx.copy_cursor
            if cy < s.rows - 1:
                ctx.copy_cursor = (cy + 1, cx)
            elif ctx.copy_scroll_offset > 0:
                ctx.copy_scroll_offset -= 1
        ctx.dirty = True
        _sync_attrs(ctx, s)
        return

    if key.name == "KEY_LEFT" or key_char == "h":
        if ctx.copy_cursor:
            cy, cx = ctx.copy_cursor
            ctx.copy_cursor = (cy, max(0, cx - 1))
        ctx.dirty = True
        _sync_attrs(ctx, s)
        return

    if key.name == "KEY_RIGHT" or key_char == "l":
        if ctx.copy_cursor:
            cy, cx = ctx.copy_cursor
            ctx.copy_cursor = (cy, min(s.cols - 1, cx + 1))
        ctx.dirty = True
        _sync_attrs(ctx, s)
        return

    if key.name == "KEY_HOME":
        if ctx.copy_cursor:
            cy, cx = ctx.copy_cursor
            ctx.copy_cursor = (cy, 0)
        ctx.dirty = True
        _sync_attrs(ctx, s)
        return

    if key.name == "KEY_END":
        if ctx.copy_cursor:
            cy, cx = ctx.copy_cursor
            ctx.copy_cursor = (cy, s.cols - 1)
        ctx.dirty = True
        _sync_attrs(ctx, s)
        return

    if key_char == "g":
        ctx.copy_scroll_offset = s.scrollback_len
        ctx.copy_cursor = (0, 0)
        ctx.dirty = True
        _sync_attrs(ctx, s)
        return

    if key_char == "G":
        ctx.copy_scroll_offset = 0
        ctx.copy_cursor = (s.rows - 1, 0)
        ctx.dirty = True
        _sync_attrs(ctx, s)
        return

    if key_char == "V":
        ctx.copy_line_mode = not ctx.copy_line_mode
        if ctx.copy_line_mode:
            ctx.copy_rect_mode = False
            s.copy_rect_mode = False
        s.copy_line_mode = ctx.copy_line_mode
        ctx.dirty = True
        return

    if key.name == "KEY_CTRL_V":
        ctx.copy_rect_mode = not ctx.copy_rect_mode
        if ctx.copy_rect_mode:
            ctx.copy_line_mode = False
            s.copy_line_mode = False
        s.copy_rect_mode = ctx.copy_rect_mode
        ctx.dirty = True
        return

    if key.name == "KEY_CTRL_U":
        half = max(1, s.rows // 2)
        ctx.copy_scroll_offset = min(ctx.copy_scroll_offset + half, s.scrollback_len)
        if ctx.copy_cursor:
            cy, cx = ctx.copy_cursor
            ctx.copy_cursor = (max(0, cy - half), cx)
        ctx.dirty = True
        _sync_attrs(ctx, s)
        return

    if key.name == "KEY_CTRL_D":
        half = max(1, s.rows // 2)
        ctx.copy_scroll_offset = max(ctx.copy_scroll_offset - half, 0)
        if ctx.copy_cursor:
            cy, cx = ctx.copy_cursor
            ctx.copy_cursor = (min(s.rows - 1, cy + half), cx)
        ctx.dirty = True
        _sync_attrs(ctx, s)
        return

    if key_char == "/":
        ctx.copy_search_active = True
        ctx.copy_search_query = ""
        ctx.copy_search_direction = "forward"
        ctx.dirty = True
        return

    if key_char == "?":
        ctx.copy_search_active = True
        ctx.copy_search_query = ""
        ctx.copy_search_direction = "backward"
        ctx.dirty = True
        return

    if key_char == "n":
        _jump_next_match(ctx, s)
        return

    if key_char == "N":
        _jump_prev_match(ctx, s)
        return

    if key_char == "y":
        if ctx.copy_anchor is not None and ctx.copy_cursor is not None:
            text = _extract_selected_text(s, ctx.copy_anchor, ctx.copy_cursor, ctx.copy_scroll_offset, rect_mode=ctx.copy_rect_mode)
            _copy_to_clipboard(text)
        _exit_copy_mode(ctx, s)
        return

    if key.name == "KEY_ENTER" or key_char == " ":
        if ctx.copy_cursor is not None:
            if ctx.copy_anchor is None:
                ctx.copy_anchor = ctx.copy_cursor
            else:
                ctx.copy_anchor = None
        ctx.dirty = True
        _sync_attrs(ctx, s)
        return

    ctx.dirty = True
    _sync_attrs(ctx, s)


def _handle_search_input(key, ctx: AppContext, s) -> None:
    if key.name == "KEY_ESCAPE":
        ctx.copy_search_active = False
        if not ctx.copy_search_query:
            ctx.copy_search_query = ""
            ctx.copy_search_matches = []
            ctx.copy_search_match_idx = -1
        ctx.dirty = True
        return

    if key.name == "KEY_ENTER" or key.name == "KEY_KP_ENTER":
        ctx.copy_search_active = False
        if ctx.copy_search_query:
            matches = _do_search(s, ctx.copy_search_query, ctx.copy_search_direction, 0, 0)
            ctx.copy_search_matches = matches
            ctx.copy_search_match_idx = -1
            if matches:
                if ctx.copy_search_direction == "backward":
                    cur_logical = s.scrollback_len - ctx.copy_scroll_offset + (ctx.copy_cursor[0] if ctx.copy_cursor else 0)
                    best = -1
                    for i, (my, mx, ml) in enumerate(matches):
                        if my < cur_logical or (my == cur_logical and mx < (ctx.copy_cursor[1] if ctx.copy_cursor else 0)):
                            best = i
                    if best >= 0:
                        _jump_to_match(ctx, s, matches, best)
                    else:
                        _jump_to_match(ctx, s, matches, len(matches) - 1)
                else:
                    cur_logical = s.scrollback_len - ctx.copy_scroll_offset + (ctx.copy_cursor[0] if ctx.copy_cursor else 0)
                    best = -1
                    for i, (my, mx, ml) in enumerate(matches):
                        if my > cur_logical or (my == cur_logical and mx > (ctx.copy_cursor[1] if ctx.copy_cursor else 0)):
                            best = i
                            break
                    if best >= 0:
                        _jump_to_match(ctx, s, matches, best)
                    else:
                        _jump_to_match(ctx, s, matches, 0)
        ctx.dirty = True
        _sync_attrs(ctx, s)
        return

    if key.name == "KEY_BACKSPACE" or key.name == "KEY_DELETE":
        if ctx.copy_search_query:
            ctx.copy_search_query = ctx.copy_search_query[:-1]
            _incremental_search(ctx, s)
        else:
            ctx.copy_search_active = False
        ctx.dirty = True
        return

    if not key.is_sequence:
        ctx.copy_search_query += str(key)
        _incremental_search(ctx, s)
        ctx.dirty = True
        return


def _incremental_search(ctx: AppContext, s) -> None:
    if not ctx.copy_search_query:
        ctx.copy_search_matches = []
        ctx.copy_search_match_idx = -1
        _sync_attrs(ctx, s)
        return
    matches = _do_search(s, ctx.copy_search_query, ctx.copy_search_direction, 0, 0)
    ctx.copy_search_matches = matches
    ctx.copy_search_match_idx = -1
    if matches:
        cur_logical = s.scrollback_len - ctx.copy_scroll_offset + (ctx.copy_cursor[0] if ctx.copy_cursor else 0)
        if ctx.copy_search_direction == "backward":
            best = -1
            for i, (my, mx, ml) in enumerate(matches):
                if my < cur_logical or (my == cur_logical and mx < (ctx.copy_cursor[1] if ctx.copy_cursor else 0)):
                    best = i
            if best >= 0:
                _jump_to_match(ctx, s, matches, best)
            else:
                _jump_to_match(ctx, s, matches, len(matches) - 1)
        else:
            best = -1
            for i, (my, mx, ml) in enumerate(matches):
                if my > cur_logical or (my == cur_logical and mx > (ctx.copy_cursor[1] if ctx.copy_cursor else 0)):
                    best = i
                    break
            if best >= 0:
                _jump_to_match(ctx, s, matches, best)
            else:
                _jump_to_match(ctx, s, matches, 0)
    _sync_attrs(ctx, s)


def _jump_next_match(ctx: AppContext, s) -> None:
    matches = ctx.copy_search_matches
    if not matches:
        return
    idx = ctx.copy_search_match_idx
    if ctx.copy_search_direction == "backward":
        idx = idx - 1 if idx > 0 else len(matches) - 1
    else:
        idx = idx + 1 if idx < len(matches) - 1 else 0
    _jump_to_match(ctx, s, matches, idx)
    _sync_attrs(ctx, s)
    ctx.dirty = True


def _jump_prev_match(ctx: AppContext, s) -> None:
    matches = ctx.copy_search_matches
    if not matches:
        return
    idx = ctx.copy_search_match_idx
    if ctx.copy_search_direction == "backward":
        idx = idx + 1 if idx < len(matches) - 1 else 0
    else:
        idx = idx - 1 if idx > 0 else len(matches) - 1
    _jump_to_match(ctx, s, matches, idx)
    _sync_attrs(ctx, s)
    ctx.dirty = True


def _sync_attrs(ctx: AppContext, s) -> None:
    if ctx.copy_anchor is not None and ctx.copy_cursor is not None:
        s.copy_sel_start = ctx.copy_anchor
        s.copy_sel_end = ctx.copy_cursor
    else:
        s.copy_sel_start = None
        s.copy_sel_end = None
    if ctx.copy_cursor is not None:
        s.copy_cursor_pos = ctx.copy_cursor
    else:
        s.copy_cursor_pos = None
    s.copy_scroll_offset = ctx.copy_scroll_offset
    if ctx.copy_search_query:
        search_lines: set[int] = set()
        for my, mx, mlen in ctx.copy_search_matches:
            search_lines.add(my)
        s.copy_search_matches = ctx.copy_search_matches
    else:
        s.copy_search_matches = None


def _exit_copy_mode(ctx: AppContext, s) -> None:
    ctx.mode = "normal"
    ctx.copy_anchor = None
    ctx.copy_cursor = None
    ctx.copy_pane = None
    ctx.copy_scroll_offset = 0
    ctx.copy_search_query = ""
    ctx.copy_search_direction = ""
    ctx.copy_search_active = False
    ctx.copy_search_matches = []
    ctx.copy_search_match_idx = -1
    ctx.copy_line_mode = False
    ctx.copy_rect_mode = False
    s.copy_sel_start = None
    s.copy_sel_end = None
    s.copy_cursor_pos = None
    s.copy_scroll_offset = 0
    s.copy_search_matches = None
    s.copy_line_mode = False
    s.copy_rect_mode = False
    s._line_cache.clear()
    s._last_cursor_y = -1
    s._last_cursor_x = -1
    ctx.dirty = True

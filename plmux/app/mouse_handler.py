"""Mouse event handling extracted from the main event loop."""

from __future__ import annotations

import re

from blessed.keyboard import Keystroke

from plmux.ui.geometry import assign_rects, adjust_ratio


def parse_mouse_event(seq: str) -> dict | None:
    try:
        if seq.startswith("\x1b[M") and len(seq) >= 6:
            cb = ord(seq[3]) - 32
            cx = ord(seq[4]) - 32 - 1
            cy = ord(seq[5]) - 32 - 1
            return {"x": cx, "y": cy, "button": cb}
        if seq.startswith("\x1b[<"):
            m = re.match(r"\x1b\[<(\d+);(\d+);(\d+)([mM])", seq)
            if m:
                b = int(m.group(1))
                x = int(m.group(2)) - 1
                y = int(m.group(3)) - 1
                typ = m.group(4)
                if b in (64, 65):
                    return {"x": x, "y": y, "button": b, "type": "scroll"}
                return {"x": x, "y": y, "button": b, "type": typ}
    except Exception:
        return None
    return None


_BORDER_TOLERANCE = 2


def detect_border_at(
    tree, rects: dict, x: int, y: int, inner_rows: int, inner_cols: int
) -> tuple[str, int, int] | None:
    if len(rects) < 2:
        return None
    best: tuple[int, tuple[str, int, int]] | None = None
    for idx_a, r_a in rects.items():
        for idx_b, r_b in rects.items():
            if idx_a >= idx_b:
                continue
            if r_a.col + r_a.cols == r_b.col and r_a.row <= y < r_a.row + r_a.rows:
                border_x = r_a.col + r_a.cols - 1
                dist = abs(x - border_x)
                if dist <= _BORDER_TOLERANCE:
                    if best is None or dist < best[0]:
                        best = (dist, ("col", idx_a, idx_b))
            if r_a.row + r_a.rows == r_b.row and r_a.col <= x < r_a.col + r_a.cols:
                border_y = r_a.row + r_a.rows - 1
                dist = abs(y - border_y)
                if dist <= _BORDER_TOLERANCE:
                    if best is None or dist < best[0]:
                        best = (dist, ("row", idx_a, idx_b))
    return best[1] if best is not None else None


def _pane_indices(tree) -> set[int]:
    if isinstance(tree, int):
        return {tree}
    _, _, a, b = tree
    return _pane_indices(a) | _pane_indices(b)


def find_resize_direction(tree, idx_a: int, idx_b: int) -> tuple[str, float] | None:
    stack: list[tuple] = [(tree, None)]
    while stack:
        node, parent_info = stack.pop()
        if isinstance(node, int):
            continue
        d, ratio, a, b = node
        a_indices = _pane_indices(a)
        b_indices = _pane_indices(b)
        if idx_a in a_indices and idx_b in b_indices:
            return (d, ratio)
        if idx_b in a_indices and idx_a in b_indices:
            return (d, ratio)
        stack.append((a, (d, ratio)))
        stack.append((b, (d, ratio)))
    return None


_SGR_MOUSE_RE = re.compile(
    r"\x1b\[<?(?P<b>\d+);(?P<x>\d+);(?P<y>\d+)(?P<type>[mM])"
)


def make_mouse_keystroke(ucs: str, m):
    ks = Keystroke(ucs=ucs[: m.end()], mode=1006, match=m)
    return ks


SGR_MOUSE_RE = _SGR_MOUSE_RE


def handle_mouse_event(
    key,
    ctx,
    ws,
    inner_rows: int,
    inner_cols: int,
) -> bool:
    key_name = getattr(key, "name", None) or ""
    if not key_name.startswith("MOUSE_"):
        return False

    try:
        rects = assign_rects(ws.tree, 0, 0, inner_rows, inner_cols)
        mx, my = key.mouse_xy
        if mx < 0 or my < 0:
            return True

        focused_s = ws.sessions[ws.focus_pane] if ws.sessions else None
        child_mouse = focused_s.screen.mouse_mode if focused_s else 0
        if child_mouse and focused_s is not None:
            raw = str(key)
            if raw:
                focused_s.write_text(raw)
            return True

        is_scroll = key_name in ("MOUSE_SCROLL_UP", "MOUSE_SCROLL_DOWN")
        is_scroll_up = key_name == "MOUSE_SCROLL_UP"
        is_release = "RELEASED" in key_name
        is_motion = "MOTION" in key_name
        is_press = not is_release and not is_motion and not is_scroll

        if ctx.mouse_resize_active:
            if is_release:
                ctx.mouse_resize_active = False
                ctx.dirty = True
            elif is_motion or is_press:
                dx = mx - ctx.mouse_resize_start_x
                dy = my - ctx.mouse_resize_start_y
                if ctx.mouse_resize_tree is not None:
                    resize_dir, resize_pane_a, resize_pane_b = ctx.mouse_resize_tree
                    if resize_dir == "col" and inner_cols > 0:
                        delta = dx / inner_cols
                        direction = "right" if delta > 0 else "left"
                        delta = abs(delta)
                        if delta > 0.005:
                            new_tree = adjust_ratio(ws.tree, resize_pane_a, direction, delta)
                            if new_tree is not None:
                                ws.tree = new_tree
                            ctx.mouse_resize_start_x = mx
                            ctx.mouse_resize_start_y = my
                    elif resize_dir == "row" and inner_rows > 0:
                        delta = dy / inner_rows
                        direction = "down" if delta > 0 else "up"
                        delta = abs(delta)
                        if delta > 0.005:
                            new_tree = adjust_ratio(ws.tree, resize_pane_a, direction, delta)
                            if new_tree is not None:
                                ws.tree = new_tree
                            ctx.mouse_resize_start_x = mx
                            ctx.mouse_resize_start_y = my
                ctx.dirty = True
        elif is_scroll:
            for idx, r in rects.items():
                if r.row <= my < (r.row + r.rows) and r.col <= mx < (r.col + r.cols):
                    ws.focus_pane = idx
                    s = ws.sessions[idx]
                    if ctx.mode == "copy" or ctx.copy_pane == idx:
                        if is_scroll_up:
                            ctx.copy_scroll_offset = min(ctx.copy_scroll_offset + 3, s.scrollback_len)
                        else:
                            ctx.copy_scroll_offset = max(ctx.copy_scroll_offset - 3, 0)
                        if ctx.copy_cursor:
                            cy, cx = ctx.copy_cursor
                            if is_scroll_up:
                                cy = max(0, cy - 3)
                            else:
                                cy = min(s.rows - 1, cy + 3)
                            ctx.copy_cursor = (cy, cx)
                            s.copy_cursor_pos = ctx.copy_cursor
                        s.copy_scroll_offset = ctx.copy_scroll_offset
                        if ctx.copy_scroll_offset == 0 and not is_scroll_up:
                            from plmux.modes.copy_mode import _exit_copy_mode
                            _exit_copy_mode(ctx, s)
                    else:
                        cur = s.scroll_offset
                        if is_scroll_up:
                            cur = min(cur + 3, s.scrollback_len)
                        else:
                            cur = max(cur - 3, 0)
                        s.scroll_offset = cur
                    ctx.dirty = True
                    break
        else:
            border = detect_border_at(ws.tree, rects, mx, my, inner_rows, inner_cols)
            if border and is_press:
                ctx.mouse_resize_active = True
                ctx.mouse_resize_start_x = mx
                ctx.mouse_resize_start_y = my
                ctx.mouse_resize_tree = border
                ctx.dirty = True
            else:
                for idx, r in rects.items():
                    if r.row <= my < (r.row + r.rows) and r.col <= mx < (r.col + r.cols):
                        ws.focus_pane = idx
                        ctx.dirty = True
                        local_y = my - r.row
                        local_x = mx - r.col
                        if is_press:
                            if ctx.mode == "copy":
                                ctx.copy_cursor = (
                                    max(0, min(local_y, ws.sessions[idx].rows - 1)),
                                    max(0, min(local_x, ws.sessions[idx].cols - 1)),
                                )
                                ctx.copy_pane = idx
                                ws.sessions[idx].copy_sel_end = ctx.copy_cursor
                            ctx.mouse_dragging = True
                            ctx.mouse_drag_pane = idx
                        elif is_release:
                            ctx.mouse_dragging = False
                            ctx.mouse_drag_pane = None
                        break
    except Exception:
        pass

    return True

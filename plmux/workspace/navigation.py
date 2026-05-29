from plmux.ui.geometry import Rect


def direction_score(cur: Rect, target: Rect, direction: str) -> float | None:
    cur_cx = cur.col + cur.cols / 2
    cur_cy = cur.row + cur.rows / 2
    tgt_cx = target.col + target.cols / 2
    tgt_cy = target.row + target.rows / 2
    dx = tgt_cx - cur_cx
    dy = tgt_cy - cur_cy
    if direction == "left":
        if dx >= 0:
            return None
        overlap = vertical_overlap(cur, target)
        if overlap <= 0:
            return None
        return -dx
    elif direction == "right":
        if dx <= 0:
            return None
        overlap = vertical_overlap(cur, target)
        if overlap <= 0:
            return None
        return dx
    elif direction == "up":
        if dy >= 0:
            return None
        overlap = horizontal_overlap(cur, target)
        if overlap <= 0:
            return None
        return -dy
    elif direction == "down":
        if dy <= 0:
            return None
        overlap = horizontal_overlap(cur, target)
        if overlap <= 0:
            return None
        return dy
    return None


def vertical_overlap(a: Rect, b: Rect) -> int:
    top = max(a.row, b.row)
    bot = min(a.row + a.rows, b.row + b.rows)
    return max(0, bot - top)


def horizontal_overlap(a: Rect, b: Rect) -> int:
    left = max(a.col, b.col)
    right = min(a.col + a.cols, b.col + b.cols)
    return max(0, right - left)

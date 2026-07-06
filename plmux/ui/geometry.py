"""Pane tree layout: tmux-like splits as a binary tree of pane indices."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal, Tuple, Union

Tree = Union[int, Tuple[Literal["row", "col"], float, "Tree", "Tree"]]


def count_panes(tree: Tree) -> int:
    if isinstance(tree, int):
        return 1
    _, _, a, b = tree
    return count_panes(a) + count_panes(b)


def pane_indices(tree: Tree) -> List[int]:
    if isinstance(tree, int):
        return [tree]
    _, _, a, b = tree
    return pane_indices(a) + pane_indices(b)


def replace_pane(tree: Tree, target: int, replacement: Tree) -> Tree:
    if tree == target:
        return replacement
    if isinstance(tree, tuple):
        d, r, a, b = tree
        return (d, r, replace_pane(a, target, replacement), replace_pane(b, target, replacement))
    return tree


def remove_pane_collapse(tree: Tree, target: int) -> Tree | None:
    if isinstance(tree, int):
        return None if tree == target else tree
    d, r, a, b = tree
    if isinstance(a, int) and a == target:
        return b
    if isinstance(b, int) and b == target:
        return a
    na = remove_pane_collapse(a, target)
    nb = remove_pane_collapse(b, target)
    if na is None:
        return nb
    if nb is None:
        return na
    return (d, r, na, nb)


def reindex_after_remove(tree: Tree, removed_idx: int) -> Tree:
    if isinstance(tree, int):
        return tree - 1 if tree > removed_idx else tree
    d, r, a, b = tree
    return (d, r, reindex_after_remove(a, removed_idx), reindex_after_remove(b, removed_idx))


def rotate_leaves(tree: Tree, direction: str = "up") -> Tree:
    """Rotate pane indices within the tree layout (structure unchanged).

    direction="up":   [0,1,2,3] -> [1,2,3,0]  (first leaf moves to last)
    direction="down": [0,1,2,3] -> [3,0,1,2]  (last leaf moves to first)
    """
    indices = pane_indices(tree)
    if len(indices) <= 1:
        return tree
    if direction == "up":
        shifted = indices[1:] + [indices[0]]
    else:
        shifted = [indices[-1]] + indices[:-1]
    mapping = dict(zip(indices, shifted))

    def _remap(t: Tree) -> Tree:
        if isinstance(t, int):
            return mapping.get(t, t)
        d, r, a, b = t
        return (d, r, _remap(a), _remap(b))

    return _remap(tree)


def adjust_ratio(tree: Tree, pane_idx: int, direction: str, delta: float = 0.05) -> Tree | None:
    """Adjust the split ratio for the ancestor node that controls `direction` for `pane_idx`.
    Returns new tree or None if no applicable ancestor found."""
    if isinstance(tree, int):
        return None

    d, r, a, b = tree

    if isinstance(a, int) and a == pane_idx:
        if (direction in ("left", "up") and d == "row") or (direction in ("up", "left") and d == "col"):
            new_r = max(0.05, min(0.95, r - delta))
            return (d, new_r, a, b)
        elif (direction in ("right", "down") and d == "row") or (direction in ("down", "right") and d == "col"):
            new_r = max(0.05, min(0.95, r + delta))
            return (d, new_r, a, b)
    if isinstance(b, int) and b == pane_idx:
        if (direction in ("left", "up") and d == "row") or (direction in ("up", "left") and d == "col"):
            new_r = max(0.05, min(0.95, r - delta))
            return (d, new_r, a, b)
        elif (direction in ("right", "down") and d == "row") or (direction in ("down", "right") and d == "col"):
            new_r = max(0.05, min(0.95, r + delta))
            return (d, new_r, a, b)

    ra = adjust_ratio(a, pane_idx, direction, delta)
    if ra is not None:
        return (d, r, ra, b)
    rb = adjust_ratio(b, pane_idx, direction, delta)
    if rb is not None:
        return (d, r, a, rb)
    return None


@dataclass
class Rect:
    row: int
    col: int
    rows: int
    cols: int


def assign_rects(
    tree: Tree,
    row: int,
    col: int,
    rows: int,
    cols: int,
    default_ratio: float = 0.5,
) -> Dict[int, Rect]:
    out: Dict[int, Rect] = {}

    def walk(t: Tree, r: int, c: int, nr: int, nc: int) -> None:
        if isinstance(t, int):
            out[t] = Rect(r, c, max(1, nr), max(1, nc))
            return
        d, ratio, a, b = t
        if d == "row":
            left_w = max(1, int(nc * ratio))
            if left_w >= nc:
                left_w = max(1, nc - 1)
            right_w = max(1, nc - left_w)
            walk(a, r, c, nr, left_w)
            walk(b, r, c + left_w, nr, right_w)
        else:
            top_h = max(1, int(nr * ratio))
            if top_h >= nr:
                top_h = max(1, nr - 1)
            bot_h = max(1, nr - top_h)
            walk(a, r, c, top_h, nc)
            walk(b, r + top_h, c, bot_h, nc)

    walk(tree, row, col, max(1, rows), max(1, cols))
    return out


def get_pane_outer_position(
    pane_idx: int,
    tree: Tree,
    status_position: str,
    content_rows: int,
    content_cols: int,
) -> tuple[int, int]:
    """Return (outer_row, outer_col) of a pane's top-left content corner
    in the outer terminal coordinate system (1-indexed).

    Accounts for status bar offset and pane Panel 1-char border.
    """
    rects = assign_rects(tree, 0, 0, content_rows, content_cols)
    r = rects.get(pane_idx)
    if r is None:
        return 1, 1
    row_off = 1 if status_position == "top" else 0
    return row_off + r.row + 1, r.col + 1
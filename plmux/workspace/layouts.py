from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from plmux.ui.geometry import Tree


LAYOUT_CYCLE = [
    "even",
    "main-vertical",
    "main-horizontal",
]


@dataclass
class LayoutTemplate:
    name: str
    description: str
    min_panes: int
    ascii_preview: list[str]


LAYOUT_TEMPLATES: list[LayoutTemplate] = [
    LayoutTemplate(
        name="even-horizontal",
        description="Even horizontal split",
        min_panes=2,
        ascii_preview=[
            "┌──────┬──────┐",
            "│      │      │",
            "│  P1  │  P2  │",
            "│      │      │",
            "└──────┴──────┘",
        ],
    ),
    LayoutTemplate(
        name="even-vertical",
        description="Even vertical split",
        min_panes=2,
        ascii_preview=[
            "┌────────────┐",
            "│     P1     │",
            "├────────────┤",
            "│     P2     │",
            "└────────────┘",
        ],
    ),
    LayoutTemplate(
        name="main-vertical",
        description="Main left + stack right",
        min_panes=3,
        ascii_preview=[
            "┌────────┬─────┐",
            "│        │ P2  │",
            "│  Main  ├─────┤",
            "│        │ P3  │",
            "└────────┴─────┘",
        ],
    ),
    LayoutTemplate(
        name="main-horizontal",
        description="Main top + stack bottom",
        min_panes=3,
        ascii_preview=[
            "┌────────────┐",
            "│    Main    │",
            "├──────┬─────┤",
            "│  P2  │ P3  │",
            "└──────┴─────┘",
        ],
    ),
    LayoutTemplate(
        name="quad",
        description="2x2 grid",
        min_panes=4,
        ascii_preview=[
            "┌──────┬──────┐",
            "│  P1  │  P2  │",
            "├──────┼──────┤",
            "│  P3  │  P4  │",
            "└──────┴──────┘",
        ],
    ),
    LayoutTemplate(
        name="columns",
        description="Three equal columns",
        min_panes=3,
        ascii_preview=[
            "┌────┬────┬────┐",
            "│    │    │    │",
            "│ P1 │ P2 │ P3 │",
            "│    │    │    │",
            "└────┴────┴────┘",
        ],
    ),
    LayoutTemplate(
        name="rows",
        description="Three equal rows",
        min_panes=3,
        ascii_preview=[
            "┌────────────┐",
            "│     P1     │",
            "├────────────┤",
            "│     P2     │",
            "├────────────┤",
            "│     P3     │",
            "└────────────┘",
        ],
    ),
    LayoutTemplate(
        name="tall",
        description="Main left + 2 rows right",
        min_panes=3,
        ascii_preview=[
            "┌────────┬─────┐",
            "│        │ P2  │",
            "│  Main  ├─────┤",
            "│        │ P3  │",
            "└────────┴─────┘",
        ],
    ),
    LayoutTemplate(
        name="wide",
        description="Main top + 2 cols bottom",
        min_panes=3,
        ascii_preview=[
            "┌────────────┐",
            "│    Main    │",
            "├──────┬─────┤",
            "│  P2  │ P3  │",
            "└──────┴─────┘",
        ],
    ),
    LayoutTemplate(
        name="fullscreen",
        description="Single pane fullscreen",
        min_panes=1,
        ascii_preview=[
            "┌────────────┐",
            "│            │",
            "│    Full    │",
            "│            │",
            "└────────────┘",
        ],
    ),
    LayoutTemplate(
        name="main-vertical-70",
        description="Main left 70% + stack right",
        min_panes=3,
        ascii_preview=[
            "┌──────────┬────┐",
            "│          │ P2 │",
            "│   Main   ├────┤",
            "│   70%    │ P3 │",
            "└──────────┴────┘",
        ],
    ),
    LayoutTemplate(
        name="main-horizontal-70",
        description="Main top 70% + stack bottom",
        min_panes=3,
        ascii_preview=[
            "┌────────────┐",
            "│    Main    │",
            "│    70%     │",
            "├──────┬─────┤",
            "│  P2  │ P3  │",
            "└──────┴─────┘",
        ],
    ),
    LayoutTemplate(
        name="triple-columns",
        description="Three columns: main + 2 side",
        min_panes=3,
        ascii_preview=[
            "┌────┬──────┬────┐",
            "│    │      │    │",
            "│ P1 │ Main │ P3 │",
            "│    │      │    │",
            "└────┴──────┴────┘",
        ],
    ),
    LayoutTemplate(
        name="quad-vertical",
        description="4 equal rows",
        min_panes=4,
        ascii_preview=[
            "┌────────────┐",
            "│     P1     │",
            "├────────────┤",
            "│     P2     │",
            "├────────────┤",
            "│     P3     │",
            "├────────────┤",
            "│     P4     │",
            "└────────────┘",
        ],
    ),
    LayoutTemplate(
        name="quad-horizontal",
        description="4 equal columns",
        min_panes=4,
        ascii_preview=[
            "┌────┬────┬────┬────┐",
            "│    │    │    │    │",
            "│ P1 │ P2 │ P3 │ P4 │",
            "│    │    │    │    │",
            "└────┴────┴────┴────┘",
        ],
    ),
    LayoutTemplate(
        name="six-grid",
        description="2x3 grid",
        min_panes=6,
        ascii_preview=[
            "┌────┬────┬────┐",
            "│ P1 │ P2 │ P3 │",
            "├────┼────┼────┤",
            "│ P4 │ P5 │ P6 │",
            "└────┴────┴────┘",
        ],
    ),
    LayoutTemplate(
        name="main-center",
        description="Main center + 2 side panels",
        min_panes=3,
        ascii_preview=[
            "┌────┬──────┬────┐",
            "│    │      │    │",
            "│ P1 │ Main │ P3 │",
            "│    │      │    │",
            "└────┴──────┴────┘",
        ],
    ),
    LayoutTemplate(
        name="monitor",
        description="Main top + 3 bottom",
        min_panes=4,
        ascii_preview=[
            "┌────────────┐",
            "│    Main    │",
            "├────┬───┬───┤",
            "│ P2 │P3 │P4 │",
            "└────┴───┴───┘",
        ],
    ),
    LayoutTemplate(
        name="developer",
        description="Editor + terminal + sidebar",
        min_panes=3,
        ascii_preview=[
            "┌──────┬──────────┐",
            "│      │          │",
            "│ Side │  Editor  │",
            "│      ├──────────┤",
            "│      │ Terminal │",
            "└──────┴──────────┘",
        ],
    ),
    LayoutTemplate(
        name="five-panes",
        description="Main + 4 corner panes",
        min_panes=5,
        ascii_preview=[
            "┌────┬──────┬────┐",
            "│ P1 │      │ P2 │",
            "├────┤ Main ├────┤",
            "│ P4 │      │ P3 │",
            "└────┴──────┴────┘",
        ],
    ),
]


def build_custom_tree(panes: list[int], direction: str, ratio: float) -> Tree:
    n = len(panes)
    if n == 0:
        return 0
    if n == 1:
        return panes[0]
    mid = n // 2
    left = build_custom_tree(panes[:mid], direction, ratio)
    right = build_custom_tree(panes[mid:], direction, ratio)
    return (direction, ratio, left, right)


def build_template_tree(panes: list[int], name: str) -> Tree | None:
    n = len(panes)
    if n == 0:
        return 0
    if n == 1:
        return panes[0]

    from plmux.extensions.registry import get_layout_algorithm
    plugin_algo = get_layout_algorithm(name)
    if plugin_algo is not None:
        try:
            result = plugin_algo(n, 80, 24)
            if result is not None:
                return result
        except Exception:
            pass

    builder = _BUILDERS.get(name)
    if builder is not None:
        return builder(panes)
    return None


def build_layout(panes: list[int], name: str) -> Tree | None:
    n = len(panes)
    if n <= 1:
        return panes[0] if panes else 0

    if name == "even":
        return build_even(panes)
    elif name == "main-vertical":
        return build_main_vertical(panes)
    elif name == "main-horizontal":
        return build_main_horizontal(panes)
    return None


def build_even(panes: list[int]) -> Tree:
    if len(panes) == 1:
        return panes[0]
    mid = len(panes) // 2
    left = build_even(panes[:mid])
    right = build_even(panes[mid:])
    return ("row", 0.5, left, right)


def build_main_vertical(panes: list[int]) -> Tree:
    if len(panes) == 1:
        return panes[0]
    main = panes[0]
    rest = panes[1:]
    if len(rest) == 1:
        return ("row", 0.6, main, rest[0])
    right_tree = build_even_vertical(rest)
    return ("row", 0.6, main, right_tree)


def build_main_horizontal(panes: list[int]) -> Tree:
    if len(panes) == 1:
        return panes[0]
    main = panes[0]
    rest = panes[1:]
    if len(rest) == 1:
        return ("col", 0.6, main, rest[0])
    bottom_tree = build_even_horizontal(rest)
    return ("col", 0.6, main, bottom_tree)


def build_even_horizontal(panes: list[int]) -> Tree:
    if len(panes) == 1:
        return panes[0]
    mid = len(panes) // 2
    left = build_even_horizontal(panes[:mid])
    right = build_even_horizontal(panes[mid:])
    return ("row", 0.5, left, right)


def build_even_vertical(panes: list[int]) -> Tree:
    if len(panes) == 1:
        return panes[0]
    mid = len(panes) // 2
    top = build_even_vertical(panes[:mid])
    bottom = build_even_vertical(panes[mid:])
    return ("col", 0.5, top, bottom)


def build_quad(panes: list[int]) -> Tree:
    if len(panes) < 4:
        return build_even_horizontal(panes)
    top_left = panes[0]
    top_right = panes[1]
    bot_left = panes[2]
    rest = panes[3:]
    if rest:
        bot_right = build_even_vertical(rest) if len(rest) > 1 else rest[0]
    else:
        bot_right = panes[3]
    top = ("row", 0.5, top_left, top_right)
    bot = ("row", 0.5, bot_left, bot_right)
    return ("col", 0.5, top, bot)


def build_columns(panes: list[int]) -> Tree:
    if len(panes) == 1:
        return panes[0]
    if len(panes) == 2:
        return ("row", 0.5, panes[0], panes[1])
    first = panes[0]
    rest = build_columns(panes[1:])
    ratio = 1.0 / len(panes)
    return ("row", ratio, first, rest)


def build_rows(panes: list[int]) -> Tree:
    if len(panes) == 1:
        return panes[0]
    if len(panes) == 2:
        return ("col", 0.5, panes[0], panes[1])
    first = panes[0]
    rest = build_rows(panes[1:])
    ratio = 1.0 / len(panes)
    return ("col", ratio, first, rest)


def build_tall(panes: list[int]) -> Tree:
    if len(panes) < 3:
        return build_main_vertical(panes)
    main = panes[0]
    top_right = panes[1]
    bottom_right = build_even_vertical(panes[2:]) if len(panes) > 3 else panes[2]
    right = ("col", 0.5, top_right, bottom_right)
    return ("row", 0.6, main, right)


def build_wide(panes: list[int]) -> Tree:
    if len(panes) < 3:
        return build_main_horizontal(panes)
    main = panes[0]
    bot_left = panes[1]
    bot_right = build_even_horizontal(panes[2:]) if len(panes) > 3 else panes[2]
    bottom = ("row", 0.5, bot_left, bot_right)
    return ("col", 0.6, main, bottom)


def build_main_vertical_70(panes: list[int]) -> Tree:
    if len(panes) == 1:
        return panes[0]
    main = panes[0]
    rest = panes[1:]
    if len(rest) == 1:
        return ("row", 0.7, main, rest[0])
    right_tree = build_even_vertical(rest)
    return ("row", 0.7, main, right_tree)


def build_main_horizontal_70(panes: list[int]) -> Tree:
    if len(panes) == 1:
        return panes[0]
    main = panes[0]
    rest = panes[1:]
    if len(rest) == 1:
        return ("col", 0.7, main, rest[0])
    bottom_tree = build_even_horizontal(rest)
    return ("col", 0.7, main, bottom_tree)


def build_triple_columns(panes: list[int]) -> Tree:
    if len(panes) < 3:
        return build_even_horizontal(panes)
    left = panes[0]
    center = panes[1]
    right_rest = panes[2:]
    right = build_even_vertical(right_rest) if len(right_rest) > 1 else right_rest[0]
    mid = ("row", 0.5, left, center)
    return ("row", 0.667, mid, right)


def build_quad_vertical(panes: list[int]) -> Tree:
    if len(panes) < 4:
        return build_even_vertical(panes)
    return build_even_vertical(panes)


def build_quad_horizontal(panes: list[int]) -> Tree:
    if len(panes) < 4:
        return build_even_horizontal(panes)
    return build_even_horizontal(panes)


def build_six_grid(panes: list[int]) -> Tree:
    if len(panes) < 6:
        return build_quad(panes)
    top = ("row", 0.333, panes[0], ("row", 0.5, panes[1], panes[2]))
    bottom = ("row", 0.333, panes[3], ("row", 0.5, panes[4], panes[5]))
    return ("col", 0.5, top, bottom)


def build_main_center(panes: list[int]) -> Tree:
    if len(panes) < 3:
        return build_even_horizontal(panes)
    left = panes[0]
    center = panes[1]
    right_rest = panes[2:]
    right = build_even_vertical(right_rest) if len(right_rest) > 1 else right_rest[0]
    left_and_center = ("row", 0.286, left, center)
    return ("row", 0.714, left_and_center, right)


def build_monitor(panes: list[int]) -> Tree:
    if len(panes) < 4:
        return build_main_horizontal(panes)
    main = panes[0]
    bot_left = panes[1]
    bot_mid = panes[2]
    bot_right_rest = panes[3:]
    if len(bot_right_rest) == 1:
        bot_right = bot_right_rest[0]
    else:
        bot_right = build_even_horizontal(bot_right_rest)
    bottom = ("row", 0.33, bot_left, ("row", 0.5, bot_mid, bot_right))
    return ("col", 0.6, main, bottom)


def build_developer(panes: list[int]) -> Tree:
    if len(panes) < 3:
        return build_main_vertical(panes)
    sidebar = panes[0]
    editor = panes[1]
    terminal_rest = panes[2:]
    if len(terminal_rest) == 1:
        terminal = terminal_rest[0]
    else:
        terminal = build_even_horizontal(terminal_rest)
    right = ("col", 0.6, editor, terminal)
    return ("row", 0.25, sidebar, right)


def build_five_panes(panes: list[int]) -> Tree:
    if len(panes) < 5:
        return build_quad(panes)
    top_left = panes[0]
    top_right = panes[1]
    center = panes[2]
    bot_right = panes[3]
    bot_left = panes[4]
    left_col = ("col", 0.5, top_left, bot_left)
    right_col = ("col", 0.5, top_right, bot_right)
    center_and_right = ("row", 0.6, center, right_col)
    return ("row", 0.25, left_col, center_and_right)


_BUILDERS: dict[str, Callable[[list[int]], Tree]] = {
    "even-horizontal": build_even_horizontal,
    "even-vertical": build_even_vertical,
    "main-vertical": build_main_vertical,
    "main-horizontal": build_main_horizontal,
    "quad": build_quad,
    "columns": build_columns,
    "rows": build_rows,
    "tall": build_tall,
    "wide": build_wide,
    "fullscreen": lambda panes: panes[0],
    "main-vertical-70": build_main_vertical_70,
    "main-horizontal-70": build_main_horizontal_70,
    "triple-columns": build_triple_columns,
    "quad-vertical": build_quad_vertical,
    "quad-horizontal": build_quad_horizontal,
    "six-grid": build_six_grid,
    "main-center": build_main_center,
    "monitor": build_monitor,
    "developer": build_developer,
    "five-panes": build_five_panes,
}


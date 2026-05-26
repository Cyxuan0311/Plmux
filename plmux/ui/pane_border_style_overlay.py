"""Pane border style overlay: configure box style, title, and active indicator."""

from __future__ import annotations

from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from plmux.config.schema import PaneBorderStyle
from plmux.ui.theme import Theme


def build_pane_border_style_overlay(
    style: PaneBorderStyle,
    theme: Theme,
    *,
    cursor: int,
    terminal_width: int,
    terminal_height: int,
) -> Panel:
    content = _build_style_table(style, cursor)

    footer = Text()
    footer.append(" \u2191\u2193 ", style="bold black on #85c751")
    footer.append(" navigate  ", style="dim")
    footer.append(" Enter/Space ", style="bold black on #85c751")
    footer.append(" toggle  ", style="dim")
    footer.append(" \u2190\u2192 ", style="bold black on #85c751")
    footer.append(" cycle  ", style="dim")
    footer.append(" Esc ", style="bold black on #85c751")
    footer.append(" close", style="dim")

    inner = Table.grid(padding=(0, 1))
    inner.add_row(content)
    inner.add_row("")
    inner.add_row(footer)

    max_w = min(terminal_width - 4, 72)
    max_h = min(terminal_height - 4, 24)

    return Panel(
        inner,
        title=" PANE BORDER STYLE ",
        title_align="left",
        border_style=theme.pane_active_border,
        box=box.HEAVY,
        width=max_w,
        height=max_h,
        style=f"on {theme.status_background}",
        padding=(1, 2),
    )


def _build_style_table(style: PaneBorderStyle, cursor: int) -> Table:
    table = Table(
        show_header=True,
        box=box.SIMPLE,
        border_style="dim #665c54",
        header_style="bold #fabd2f",
        pad_edge=False,
    )
    table.add_column("", width=3)
    table.add_column("Option", width=18)
    table.add_column("Value", min_width=16)
    table.add_column("Preview", min_width=24)

    rows = _build_option_rows(style)
    for i, (option, value, preview) in enumerate(rows):
        if i == cursor:
            marker = "\u25B6"
            row_style = "bold white"
        else:
            marker = " "
            row_style = "dim white"
        table.add_row(marker, option, value, preview, style=row_style)

    return table


def _build_option_rows(style: PaneBorderStyle) -> list[tuple[str, str, str]]:
    rows = [
        ("Box Style", style.box_style, _box_style_preview(style.box_style)),
        ("Show Title", "on" if style.show_title else "off", "0:bash" if style.show_title else "(no title)"),
        ("Title Position", style.title_position, _title_position_preview(style.title_position)),
        ("Active Indicator", style.active_indicator, _active_indicator_preview(style.active_indicator)),
    ]
    return rows


def _box_style_preview(box_style: str) -> str:
    previews = {
        "square": "\u250C\u2500\u2510 \u2502 \u2514\u2500\u2518",
        "rounded": "\u256D\u2500\u256E \u2502 \u2570\u2500\u256F",
        "heavy": "\u250F\u2501\u2513 \u2503 \u2517\u2501\u251B",
        "minimal": "  - - -  ",
        "ascii": "+-+ | +-+",
        "double": "\u2554\u2550\u2557 \u2551 \u255A\u2550\u255D",
        "dotted": "\u250C\u2504\u2510 \u2506 \u2514\u2504\u2518",
    }
    return previews.get(box_style, "         ")


def _title_position_preview(pos: str) -> str:
    if pos == "left":
        return "0:bash------"
    elif pos == "center":
        return "---0:bash---"
    elif pos == "right":
        return "------0:bash"
    return pos


def _active_indicator_preview(indicator: str) -> str:
    if indicator == "color":
        return "colored border"
    elif indicator == "bold":
        return "bold border"
    elif indicator == "marker":
        return "\u25B6 prefix marker"
    return indicator


OPTION_NAMES = [
    "box_style",
    "show_title",
    "title_position",
    "active_indicator",
]


def cycle_option(style: PaneBorderStyle, option: str, direction: int = 1) -> None:
    if option == "box_style":
        opts = list(PaneBorderStyle.VALID_BOX_STYLES)
        idx = opts.index(style.box_style) if style.box_style in opts else 0
        style.box_style = opts[(idx + direction) % len(opts)]
    elif option == "show_title":
        style.show_title = not style.show_title
    elif option == "title_position":
        opts = list(PaneBorderStyle.VALID_TITLE_POSITION)
        idx = opts.index(style.title_position) if style.title_position in opts else 0
        style.title_position = opts[(idx + direction) % len(opts)]
    elif option == "active_indicator":
        opts = list(PaneBorderStyle.VALID_ACTIVE_INDICATOR)
        idx = opts.index(style.active_indicator) if style.active_indicator in opts else 0
        style.active_indicator = opts[(idx + direction) % len(opts)]


def get_option_count() -> int:
    return len(OPTION_NAMES)


def get_option_name(cursor: int) -> str:
    if 0 <= cursor < len(OPTION_NAMES):
        return OPTION_NAMES[cursor]
    return ""

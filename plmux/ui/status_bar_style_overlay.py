"""Status bar style overlay: configure separator, layout, and display options."""

from __future__ import annotations

from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from plmux.config.schema import StatusBarStyle
from plmux.ui.theme import Theme


def build_status_bar_style_overlay(
    style: StatusBarStyle,
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
    max_h = min(terminal_height - 4, 28)

    return Panel(
        inner,
        title=" STATUS BAR STYLE ",
        title_align="left",
        border_style=theme.pane_active_border,
        box=box.HEAVY,
        width=max_w,
        height=max_h,
        style=f"on {theme.status_background}",
        padding=(1, 2),
    )


def _build_style_table(style: StatusBarStyle, cursor: int) -> Table:
    table = Table(
        show_header=True,
        box=box.SIMPLE,
        border_style="dim #665c54",
        header_style="bold #fabd2f",
        pad_edge=False,
    )
    table.add_column("", width=3)
    table.add_column("Option", width=18)
    table.add_column("Value", min_width=20)
    table.add_column("Preview", min_width=22)

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


def _build_option_rows(style: StatusBarStyle) -> list[tuple[str, str, str]]:
    rows = [
        ("Separator", style.separator, _separator_preview(style.separator)),
        ("Mode Indicator", style.mode_indicator, _mode_indicator_preview(style.mode_indicator)),
        ("Show Command", "on" if style.show_command else "off", "N W0:P1 bash" if style.show_command else "N W0:P1"),
        ("Show Session", "on" if style.show_session else "off", "S0:main W0:P1" if style.show_session else "W0:P1"),
        ("Show Window Idx", "on" if style.show_window_index else "off", "W0:main" if style.show_window_index else "main"),
        ("Show Pane Idx", "on" if style.show_pane_index else "off", "W0:P1" if style.show_pane_index else "W0"),
        ("Right Sections", style.right_sections, _right_sections_preview(style.right_sections)),
        ("Spacing", style.spacing, "A  B  C" if style.spacing == "spaced" else "A|B|C"),
        ("Gradient", "on" if style.gradient else "off", "gradient bar" if style.gradient else "solid bar"),
    ]
    return rows


def _separator_preview(sep: str) -> str:
    previews = {
        "powerline": "\uE0B0\uE0B0\uE0B0",
        "powerline_round": "\uE0B4\uE0B4\uE0B4",
        "powerline_diamond": "\uE0B8\uE0B8\uE0B8",
        "ascii": "/ / /",
        "unicode": "\u2503\u2503\u2503",
        "unicode_thin": "\u2502\u2502\u2502",
        "dots": "\u00B7\u00B7\u00B7",
        "pipes": "| | |",
        "none": "     ",
    }
    return previews.get(sep, "     ")


def _mode_indicator_preview(indicator: str) -> str:
    if indicator == "full":
        return "NORMAL"
    elif indicator == "short":
        return "N"
    elif indicator == "minimal":
        return "(none)"
    return indicator


def _right_sections_preview(sections: str) -> str:
    if sections == "clock_host":
        return "12:00 host"
    elif sections == "clock":
        return "12:00"
    elif sections == "host":
        return "host"
    return ""


OPTION_NAMES = [
    "separator",
    "mode_indicator",
    "show_command",
    "show_session",
    "show_window_index",
    "show_pane_index",
    "right_sections",
    "spacing",
    "gradient",
]


def cycle_option(style: StatusBarStyle, option: str, direction: int = 1) -> None:
    if option == "separator":
        opts = list(StatusBarStyle.VALID_SEPARATORS)
        idx = opts.index(style.separator) if style.separator in opts else 0
        style.separator = opts[(idx + direction) % len(opts)]
    elif option == "mode_indicator":
        opts = list(StatusBarStyle.VALID_MODE_INDICATOR)
        idx = opts.index(style.mode_indicator) if style.mode_indicator in opts else 0
        style.mode_indicator = opts[(idx + direction) % len(opts)]
    elif option == "show_command":
        style.show_command = not style.show_command
    elif option == "show_session":
        style.show_session = not style.show_session
    elif option == "show_window_index":
        style.show_window_index = not style.show_window_index
    elif option == "show_pane_index":
        style.show_pane_index = not style.show_pane_index
    elif option == "right_sections":
        opts = list(StatusBarStyle.VALID_RIGHT_SECTIONS)
        idx = opts.index(style.right_sections) if style.right_sections in opts else 0
        style.right_sections = opts[(idx + direction) % len(opts)]
    elif option == "spacing":
        opts = list(StatusBarStyle.VALID_SPACING)
        idx = opts.index(style.spacing) if style.spacing in opts else 0
        style.spacing = opts[(idx + direction) % len(opts)]
    elif option == "gradient":
        style.gradient = not style.gradient


def get_option_count() -> int:
    return len(OPTION_NAMES)


def get_option_name(cursor: int) -> str:
    if 0 <= cursor < len(OPTION_NAMES):
        return OPTION_NAMES[cursor]
    return ""

"""Plugin list overlay: browse, enable/disable plugins with up/down + Space."""

from __future__ import annotations

from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from plmux.extensions.registry import discover_plugins, is_plugin_loaded
from plmux.ui.theme import Theme


def build_plugin_list_overlay(
    theme: Theme,
    *,
    search_paths: list[str],
    enabled_names: list[str],
    cursor: int,
    terminal_width: int,
    terminal_height: int,
) -> Panel:
    all_plugins = discover_plugins(search_paths)
    enabled_set = set(enabled_names)
    rows = [(p, p in enabled_set) for p in all_plugins]

    cursor = max(0, min(cursor, len(rows) - 1)) if rows else 0

    table = Table(
        show_header=True,
        box=box.SIMPLE,
        border_style="dim #665c54",
        header_style="bold #fabd2f",
        pad_edge=False,
    )
    table.add_column("", width=3)
    table.add_column("Plugin", style="bold #fabd2f", width=20)
    table.add_column("Status", width=10)
    table.add_column("Loaded", width=8)

    if not rows:
        table.add_row("", "(no plugins found)", "", "", style="dim white")
    else:
        for i, (name, enabled) in enumerate(rows):
            if i == cursor:
                marker = "\u25B6"
                name_style = "bold white"
            else:
                marker = " "
                name_style = "#ebdbb2"

            if enabled:
                status_text = "\u2713 ON"
                status_style = "bold #85c751"
            else:
                status_text = "\u2717 OFF"
                status_style = "dim #f92672"

            loaded = "\u25CF" if is_plugin_loaded(name) else "\u25CB"
            loaded_style = "#85c751" if is_plugin_loaded(name) else "dim #665c54"

            row_marker = Text()
            row_marker.append(marker, style=name_style)

            table.add_row(
                row_marker,
                Text(name, style=name_style),
                Text(status_text, style=status_style),
                Text(loaded, style=loaded_style),
            )

    footer = Text()
    footer.append(" \u2191\u2193 ", style="bold black on #85c751")
    footer.append(" navigate  ", style="dim")
    footer.append(" Space ", style="bold black on #85c751")
    footer.append(" toggle  ", style="dim")
    footer.append(" Esc ", style="bold black on #85c751")
    footer.append(" close", style="dim")

    inner = Table.grid(padding=(0, 1))
    inner.add_row(table)
    inner.add_row("")
    inner.add_row(footer)

    max_w = min(terminal_width - 4, 58)
    max_h = min(terminal_height - 4, 28)

    return Panel(
        inner,
        title=" PLUGINS ",
        title_align="left",
        border_style=theme.pane_active_border,
        box=box.HEAVY,
        width=max_w,
        height=max_h,
        style=f"on {theme.status_background}",
        padding=(1, 2),
    )


def get_plugin_at(search_paths: list[str], cursor: int) -> str | None:
    all_plugins = discover_plugins(search_paths)
    if not all_plugins:
        return None
    cursor = max(0, min(cursor, len(all_plugins) - 1))
    return all_plugins[cursor]

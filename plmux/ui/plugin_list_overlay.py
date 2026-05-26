"""Plugin list overlay: browse, enable/disable plugins with up/down + Space."""

from __future__ import annotations

from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from plmux.extensions.registry import discover_plugins, get_plugin_error, get_plugin_meta, is_plugin_loaded
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
    table.add_column("Version", width=8)
    table.add_column("Status", width=10)
    table.add_column("Loaded", width=8)

    if not rows:
        table.add_row("", "(no plugins found)", "", "", "", style="dim white")
    else:
        for i, (name, enabled) in enumerate(rows):
            if i == cursor:
                marker = "\u25B6"
                name_style = "bold white"
            else:
                marker = " "
                name_style = "#ebdbb2"

            meta = get_plugin_meta(name)
            version = meta.version if meta and meta.version != "0.0.0" else ""

            if enabled:
                status_text = "\u2713 ON"
                status_style = "bold #85c751"
            else:
                status_text = "\u2717 OFF"
                status_style = "dim #f92672"

            error = get_plugin_error(name)
            if error:
                loaded = "\u2717"
                loaded_style = "bold #f92672"
            elif is_plugin_loaded(name):
                loaded = "\u25CF"
                loaded_style = "#85c751"
            else:
                loaded = "\u25CB"
                loaded_style = "dim #665c54"

            row_marker = Text()
            row_marker.append(marker, style=name_style)

            table.add_row(
                row_marker,
                Text(name, style=name_style),
                Text(version, style="dim #b8bb26"),
                Text(status_text, style=status_style),
                Text(loaded, style=loaded_style),
            )

    desc_text = Text()
    if rows and 0 <= cursor < len(rows):
        selected_name = rows[cursor][0]
        meta = get_plugin_meta(selected_name)
        if meta and meta.description:
            desc_text.append(f"  {meta.description}", style="dim #ebdbb2")
        error = get_plugin_error(selected_name)
        if error:
            desc_text.append(f"  [error: {error}]", style="bold #f92672")

    footer = Text()
    footer.append(" \u2191\u2193 ", style="bold black on #85c751")
    footer.append(" navigate  ", style="dim")
    footer.append(" Space ", style="bold black on #85c751")
    footer.append(" toggle  ", style="dim")
    footer.append(" Esc ", style="bold black on #85c751")
    footer.append(" close", style="dim")

    inner = Table.grid(padding=(0, 1))
    inner.add_row(table)
    if desc_text:
        inner.add_row(desc_text)
    inner.add_row("")
    inner.add_row(footer)

    max_w = min(terminal_width - 4, 62)
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

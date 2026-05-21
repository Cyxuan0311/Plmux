"""Layout list overlay: browse layout templates with preview and apply."""

from __future__ import annotations

from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from plmux.ui.theme import Theme
from plmux.workspace import LAYOUT_TEMPLATES, LayoutTemplate


def build_layout_list_overlay(
    theme: Theme,
    *,
    cursor: int,
    current_panes: int,
    terminal_width: int,
    terminal_height: int,
) -> Panel:
    templates = LAYOUT_TEMPLATES
    if not templates:
        return Panel("No layout templates", title=" LAYOUTS ", border_style="red")

    cursor = max(0, min(cursor, len(templates) - 1))
    selected = templates[cursor]

    list_grid = Table.grid(padding=(0, 1))
    list_grid.add_column(width=22)

    for i, tpl in enumerate(templates):
        row_text = Text()
        if i == cursor:
            row_text.append(" \u25B6 ", style="bold white")
            row_text.append(tpl.name, style="bold white")
        else:
            row_text.append("   ")
            row_text.append(tpl.name, style="dim #ebdbb2")
        list_grid.add_row(row_text)

    preview = _build_preview(selected, current_panes)

    body = Table.grid(padding=(0, 3))
    body.add_column()
    body.add_column()
    body.add_row(list_grid, preview)

    footer = Text()
    footer.append(" \u2191\u2193 ", style="bold black on #85c751")
    footer.append(" navigate  ", style="dim")
    footer.append(" Enter ", style="bold black on #85c751")
    footer.append(" apply  ", style="dim")
    footer.append(" Esc ", style="bold black on #85c751")
    footer.append(" cancel", style="dim")

    inner = Table.grid(padding=(0, 1))
    inner.add_row(body)
    inner.add_row("")
    inner.add_row(footer)

    max_w = min(terminal_width - 4, 74)
    max_h = min(terminal_height - 4, 28)

    return Panel(
        inner,
        title=" LAYOUTS ",
        title_align="left",
        border_style=theme.pane_active_border,
        box=box.HEAVY,
        width=max_w,
        height=max_h,
        style=f"on {theme.status_background}",
        padding=(1, 2),
    )


def _build_preview(tpl: LayoutTemplate, current_panes: int) -> Panel:
    grid = Table.grid(padding=(0, 0))
    grid.add_column()

    grid.add_row(Text(" Preview ", style="bold underline #fabd2f"))
    grid.add_row(Text(""))

    desc = Text()
    desc.append(tpl.description, style="#ebdbb2")
    grid.add_row(desc)

    panes_info = Text()
    panes_info.append("Panes: ", style="dim #928374")
    panes_info.append(str(tpl.min_panes), style="bold #fabd2f")
    if current_panes < tpl.min_panes:
        panes_info.append(f"  (+{tpl.min_panes - current_panes} will be created)", style="dim #fe8019")
    elif current_panes > tpl.min_panes:
        panes_info.append(f"  ({current_panes - tpl.min_panes} will be closed)", style="dim #fe8019")
    else:
        panes_info.append("  \u2713 matched", style="dim #85c751")
    grid.add_row(panes_info)
    grid.add_row(Text(""))

    for line in tpl.ascii_preview:
        grid.add_row(Text(line, style="#83a598"))

    return Panel(
        grid,
        title=f" {tpl.name} ",
        title_align="left",
        border_style="dim #665c54",
        box=box.SIMPLE,
        padding=(0, 1),
    )

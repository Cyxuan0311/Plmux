"""Layout list overlay: browse layout templates with preview, apply, and custom layout builder."""

from __future__ import annotations

from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from plmux.config.schema import CustomLayoutConfig
from plmux.ui.theme import Theme
from plmux.workspace import LAYOUT_TEMPLATES, LayoutTemplate

_TAB_PRESETS = 0
_TAB_CUSTOM = 1
_NUM_TABS = 2

_AREA_SAVED = 0
_AREA_BUILDER = 1


def build_layout_list_overlay(
    theme: Theme,
    *,
    cursor: int,
    current_panes: int,
    terminal_width: int,
    terminal_height: int,
    tab: int = 0,
    custom_layouts: list[CustomLayoutConfig] | None = None,
    custom_cursor: int = 0,
    builder: dict | None = None,
) -> Panel:
    custom_layouts = custom_layouts or []
    builder = builder or _default_builder()

    tab_labels = [" Presets ", " Custom "]
    tabs_text = Text()
    for i, label in enumerate(tab_labels):
        if i == tab:
            tabs_text.append(label, style="bold white on #458588")
        else:
            tabs_text.append(label, style="dim white on #3c3836")
        if i < len(tab_labels) - 1:
            tabs_text.append(" ")

    if tab == _TAB_PRESETS:
        body = _build_presets_tab(cursor, current_panes)
    else:
        body = _build_custom_tab(custom_layouts, custom_cursor, builder, current_panes)

    footer = _build_footer(tab, builder)

    inner = Table.grid(padding=(0, 1))
    inner.add_row(tabs_text)
    inner.add_row("")
    inner.add_row(body)
    inner.add_row("")
    inner.add_row(footer)

    max_w = min(terminal_width - 4, 78)
    max_h = min(terminal_height - 4, 30)

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


def _default_builder() -> dict:
    return {
        "name": "",
        "panes": 2,
        "direction": "row",
        "ratio": 0.5,
        "field_cursor": 0,
        "area": _AREA_SAVED,
        "editing": False,
        "edit_buffer": "",
        "message": "",
    }


BUILDER_FIELDS = ["name", "panes", "direction", "ratio"]
_ACTION_APPLY = len(BUILDER_FIELDS)
_ACTION_SAVE = len(BUILDER_FIELDS) + 1
BUILDER_LABELS = {
    "name": "Name",
    "panes": "Panes",
    "direction": "Direction",
    "ratio": "Ratio",
}
BUILDER_HINTS = {
    "name": "layout name",
    "panes": "2-9",
    "direction": "row / col",
    "ratio": "0.1-0.9",
}


def _build_presets_tab(cursor: int, current_panes: int) -> Table:
    templates = list(LAYOUT_TEMPLATES)
    from plmux.extensions.registry import get_layout_algorithms
    plugin_algos = get_layout_algorithms()
    plugin_items = []
    for algo_name in sorted(plugin_algos.keys()):
        if not any(t.name == algo_name for t in templates):
            plugin_items.append(LayoutTemplate(
                name=algo_name,
                description=f"Plugin: {algo_name}",
                min_panes=1,
                ascii_preview=["[plugin layout]"],
            ))
    templates.extend(plugin_items)
    if not templates:
        return Table.grid().add_row(Text("No layout templates", style="dim"))

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
    return body


def _build_custom_tab(
    custom_layouts: list[CustomLayoutConfig],
    custom_cursor: int,
    builder: dict,
    current_panes: int,
) -> Table:
    left_w = 26
    list_grid = Table.grid(padding=(0, 1))
    list_grid.add_column(width=left_w)

    area = builder.get("area", _AREA_SAVED)

    list_grid.add_row(Text(" Saved Layouts ", style="bold underline #fabd2f"))
    list_grid.add_row(Text(""))

    if not custom_layouts:
        list_grid.add_row(Text("  (none)", style="dim #928374"))
    else:
        custom_cursor = max(0, min(custom_cursor, len(custom_layouts) - 1))
        for i, cl in enumerate(custom_layouts):
            row_text = Text()
            if area == _AREA_SAVED and i == custom_cursor:
                row_text.append(" \u25B6 ", style="bold white")
                row_text.append(cl.name or "unnamed", style="bold white")
            else:
                row_text.append("   ")
                row_text.append(cl.name or "unnamed", style="dim #ebdbb2")
            list_grid.add_row(row_text)

    list_grid.add_row(Text(""))
    list_grid.add_row(Text(" Builder ", style="bold underline #83a598"))
    list_grid.add_row(Text(""))

    fc = builder.get("field_cursor", 0)
    editing = builder.get("editing", False)
    edit_buffer = builder.get("edit_buffer", "")

    for fi, field_name in enumerate(BUILDER_FIELDS):
        label = BUILDER_LABELS[field_name]
        hint = BUILDER_HINTS.get(field_name, "")
        value = str(builder.get(field_name, ""))
        row_text = Text()
        if area == _AREA_BUILDER and fi == fc:
            row_text.append(" \u25B8 ", style="bold #fe8019")
            row_text.append(f"{label}: ", style="bold #fabd2f")
            if field_name == "direction":
                row_text.append(" \u25C4 ", style="bold #83a598")
                row_text.append(value, style="bold white on #504945")
                row_text.append(" \u25BA ", style="bold #83a598")
            elif editing and fi == fc:
                row_text.append(edit_buffer, style="bold white on #504945")
                row_text.append("\u2588", style="bold white on #504945")
            else:
                row_text.append(value, style="bold white")
                row_text.append(f"  ({hint})", style="dim #665c54")
        else:
            row_text.append("   ")
            row_text.append(f"{label}: ", style="dim #928374")
            if field_name == "direction":
                row_text.append(value, style="#ebdbb2")
            else:
                row_text.append(value, style="#ebdbb2")
        list_grid.add_row(row_text)

    list_grid.add_row(Text(""))

    for ai, (action_idx, action_label, action_style) in enumerate([
        (_ACTION_APPLY, "Apply", "bold black on #85c751"),
        (_ACTION_SAVE, "Save", "bold black on #83a598"),
    ]):
        row_text = Text()
        if area == _AREA_BUILDER and fc == action_idx:
            row_text.append(" \u25B8 ", style="bold #fe8019")
            row_text.append(f" {action_label} ", style=action_style)
        else:
            row_text.append("   ")
            row_text.append(f" {action_label} ", style=f"dim {action_style.split(' on ')[-1] if ' on ' in action_style else ''}")
        list_grid.add_row(row_text)

    msg = builder.get("message", "")
    if msg:
        list_grid.add_row(Text(""))
        list_grid.add_row(Text(f"  {msg}", style="bold #fe8019"))

    right_panel = _build_custom_preview(builder, current_panes)

    body = Table.grid(padding=(0, 2))
    body.add_column()
    body.add_column()
    body.add_row(list_grid, right_panel)
    return body


def _build_custom_preview(builder: dict, current_panes: int) -> Panel:
    grid = Table.grid(padding=(0, 0))
    grid.add_column()

    grid.add_row(Text(" Preview ", style="bold underline #fabd2f"))
    grid.add_row(Text(""))

    panes = builder.get("panes", 2)
    direction = builder.get("direction", "row")
    ratio = builder.get("ratio", 0.5)

    dir_label = "Horizontal" if direction == "row" else "Vertical"
    desc = Text()
    desc.append(f"{panes} panes, {dir_label}", style="#ebdbb2")
    desc.append(f", ratio={ratio:.0%}", style="#ebdbb2")
    grid.add_row(desc)

    panes_info = Text()
    panes_info.append("Panes: ", style="dim #928374")
    panes_info.append(str(panes), style="bold #fabd2f")
    if current_panes < panes:
        panes_info.append(f"  (+{panes - current_panes} will be created)", style="dim #fe8019")
    elif current_panes > panes:
        panes_info.append(f"  ({current_panes - panes} will be closed)", style="dim #fe8019")
    else:
        panes_info.append("  \u2713 matched", style="dim #85c751")
    grid.add_row(panes_info)
    grid.add_row(Text(""))

    ascii_lines = _generate_ascii_preview(panes, direction, ratio)
    for line in ascii_lines:
        grid.add_row(Text(line, style="#83a598"))

    return Panel(
        grid,
        title=" Custom Layout ",
        title_align="left",
        border_style="dim #665c54",
        box=box.SIMPLE,
        padding=(0, 1),
    )


def _generate_ascii_preview(panes: int, direction: str, ratio: float) -> list[str]:
    if panes <= 0:
        return ["[invalid]"]
    if panes == 1:
        return [
            "\u250c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510",
            "\u2502            \u2502",
            "\u2502    Full    \u2502",
            "\u2502            \u2502",
            "\u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518",
        ]
    if direction == "row":
        return _ascii_row_split(panes, ratio)
    return _ascii_col_split(panes)


def _ascii_row_split(panes: int, ratio: float) -> list[str]:
    total = 12
    left_w = max(2, int(total * ratio))
    right_w = max(2, total - left_w)
    top = "\u250c" + "\u2500" * left_w + "\u252c" + "\u2500" * right_w + "\u2510"
    bot = "\u2514" + "\u2500" * left_w + "\u2534" + "\u2500" * right_w + "\u2518"
    lines = [top]
    if panes == 2:
        lines.append("\u2502" + _center("P1", left_w) + "\u2502" + _center("P2", right_w) + "\u2502")
        lines.append(bot)
    else:
        lines.append("\u2502" + _center("Main", left_w) + "\u2502" + _center("P2", right_w) + "\u2502")
        lines.append("\u251c" + "\u2500" * left_w + "\u253c" + "\u2500" * right_w + "\u2524")
        for i in range(3, panes + 1):
            lines.append("\u2502" + " " * left_w + "\u2502" + _center(f"P{i}", right_w) + "\u2502")
            if i < panes:
                lines.append("\u251c" + "\u2500" * left_w + "\u253c" + "\u2500" * right_w + "\u2524")
        lines.append(bot)
    return lines


def _ascii_col_split(panes: int) -> list[str]:
    w = 12
    top = "\u250c" + "\u2500" * w + "\u2510"
    mid = "\u251c" + "\u2500" * w + "\u2524"
    bot = "\u2514" + "\u2500" * w + "\u2518"
    lines = [top]
    lines.append("\u2502" + _center("P1", w) + "\u2502")
    if panes == 2:
        lines.append(mid)
        lines.append("\u2502" + _center("P2", w) + "\u2502")
        lines.append(bot)
    else:
        lines.append(mid)
        lines.append("\u2502" + _center("Main", w) + "\u2502")
        for i in range(3, panes + 1):
            lines.append(mid)
            lines.append("\u2502" + _center(f"P{i}", w) + "\u2502")
        lines.append(bot)
    return lines


def _center(text: str, width: int) -> str:
    if len(text) >= width:
        return text[:width]
    pad = width - len(text)
    left = pad // 2
    right = pad - left
    return " " * left + text + " " * right


def _build_footer(tab: int, builder: dict | None = None) -> Text:
    footer = Text()
    footer.append(" Tab ", style="bold black on #85c751")
    footer.append(" switch  ", style="dim")
    if tab == _TAB_PRESETS:
        footer.append(" \u2191\u2193 ", style="bold black on #85c751")
        footer.append(" navigate  ", style="dim")
        footer.append(" Enter ", style="bold black on #85c751")
        footer.append(" apply  ", style="dim")
    else:
        area = (builder or {}).get("area", _AREA_SAVED)
        if area == _AREA_SAVED:
            footer.append(" \u2191\u2193 ", style="bold black on #85c751")
            footer.append(" navigate  ", style="dim")
            footer.append(" e ", style="bold black on #85c751")
            footer.append(" load  ", style="dim")
            footer.append(" d ", style="bold black on #f92672")
            footer.append(" delete  ", style="dim")
        else:
            footer.append(" \u2191\u2193 ", style="bold black on #85c751")
            footer.append(" navigate  ", style="dim")
            footer.append(" Enter ", style="bold black on #85c751")
            footer.append(" edit/execute  ", style="dim")
            footer.append(" type ", style="bold black on #85c751")
            footer.append(" quick edit  ", style="dim")
    footer.append(" Esc ", style="bold black on #85c751")
    footer.append(" cancel", style="dim")
    return footer


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

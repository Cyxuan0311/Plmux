"""Layout list mode handler: browse layout templates, custom builder, apply/save."""

from __future__ import annotations

from plmux.config.loader import save_user_config
from plmux.config.schema import CustomLayoutConfig
from plmux.modes import AppContext
from plmux.ui.layout_list_overlay import (
    BUILDER_FIELDS,
    _ACTION_APPLY,
    _ACTION_SAVE,
    _AREA_BUILDER,
    _AREA_SAVED,
    _TAB_CUSTOM,
    _TAB_PRESETS,
    _default_builder,
)
from plmux.workspace import LAYOUT_TEMPLATES


def handle_layout_list_mode(key, ctx: AppContext) -> None:
    ch = str(key)
    name = key.name if hasattr(key, "name") else ""

    if ctx.layout_list_tab == _TAB_CUSTOM:
        builder = ctx.layout_builder
        if not builder:
            builder = _default_builder()
            ctx.layout_builder = builder
        if builder.get("editing"):
            _handle_editing(ch, name, ctx, builder)
            return

    if name == "KEY_ESCAPE" or ch == "q":
        ctx.mode = "normal"
        ctx.dirty = True
        return

    if ch == "\t" or name == "KEY_TAB":
        ctx.layout_list_tab = 1 - ctx.layout_list_tab
        ctx.dirty = True
        return

    if ctx.layout_list_tab == _TAB_PRESETS:
        _handle_presets(ch, name, ctx)
    else:
        _handle_custom(ch, name, ctx)


def _handle_presets(ch: str, name: str, ctx: AppContext) -> None:
    n = len(LAYOUT_TEMPLATES)
    if n == 0:
        ctx.dirty = True
        return

    ctx.layout_list_cursor = max(0, min(ctx.layout_list_cursor, n - 1))

    if name in ("KEY_UP",) or ch == "k":
        ctx.layout_list_cursor = max(0, ctx.layout_list_cursor - 1)
        ctx.dirty = True
    elif name in ("KEY_DOWN",) or ch == "j":
        ctx.layout_list_cursor = min(n - 1, ctx.layout_list_cursor + 1)
        ctx.dirty = True
    elif name == "KEY_HOME":
        ctx.layout_list_cursor = 0
        ctx.dirty = True
    elif name == "KEY_END" or ch == "G":
        ctx.layout_list_cursor = n - 1
        ctx.dirty = True
    elif name == "KEY_PGUP":
        ctx.layout_list_cursor = max(0, ctx.layout_list_cursor - 3)
        ctx.dirty = True
    elif name == "KEY_PGDOWN":
        ctx.layout_list_cursor = min(n - 1, ctx.layout_list_cursor + 3)
        ctx.dirty = True
    elif name == "KEY_ENTER" or ch in ("\n", "\r"):
        idx = ctx.layout_list_cursor
        if idx < n:
            tpl = LAYOUT_TEMPLATES[idx]
            ctx.ws.apply_layout_template(tpl.name)
            if ctx.send_remote_command:
                ctx.send_remote_command({"action": "apply_layout_template", "name": tpl.name})
            ctx.mode = "normal"
        ctx.dirty = True
    else:
        ctx.dirty = True


def _handle_custom(ch: str, name: str, ctx: AppContext) -> None:
    builder = ctx.layout_builder
    if not builder:
        builder = _default_builder()
        ctx.layout_builder = builder

    custom_layouts = list(ctx.ws.cfg.custom_layouts)
    n_custom = len(custom_layouts)
    area = builder.get("area", _AREA_SAVED)

    if area == _AREA_SAVED and n_custom == 0:
        builder["area"] = _AREA_BUILDER
        area = _AREA_BUILDER

    if name in ("KEY_UP",) or ch == "k":
        if area == _AREA_BUILDER:
            fc = builder.get("field_cursor", 0)
            if fc > 0:
                builder["field_cursor"] = fc - 1
            elif n_custom > 0:
                builder["area"] = _AREA_SAVED
        else:
            if ctx.layout_custom_cursor > 0:
                ctx.layout_custom_cursor -= 1
        builder["message"] = ""
        ctx.dirty = True
    elif name in ("KEY_DOWN",) or ch == "j":
        if area == _AREA_SAVED:
            if ctx.layout_custom_cursor < n_custom - 1:
                ctx.layout_custom_cursor += 1
            else:
                builder["area"] = _AREA_BUILDER
                builder["field_cursor"] = 0
        else:
            fc = builder.get("field_cursor", 0)
            if fc < _ACTION_SAVE:
                builder["field_cursor"] = fc + 1
        builder["message"] = ""
        ctx.dirty = True
    elif name in ("KEY_LEFT",) or ch == "h":
        if area == _AREA_BUILDER:
            fc = builder.get("field_cursor", 0)
            if fc < len(BUILDER_FIELDS) and BUILDER_FIELDS[fc] == "direction":
                builder["direction"] = "col" if builder.get("direction", "row") == "row" else "row"
                builder["message"] = ""
        ctx.dirty = True
    elif name in ("KEY_RIGHT",) or ch == "l":
        if area == _AREA_BUILDER:
            fc = builder.get("field_cursor", 0)
            if fc < len(BUILDER_FIELDS) and BUILDER_FIELDS[fc] == "direction":
                builder["direction"] = "col" if builder.get("direction", "row") == "row" else "row"
                builder["message"] = ""
        ctx.dirty = True
    elif name == "KEY_HOME":
        if area == _AREA_BUILDER:
            builder["field_cursor"] = 0
        else:
            ctx.layout_custom_cursor = 0
        ctx.dirty = True
    elif name == "KEY_END" or ch == "G":
        if area == _AREA_BUILDER:
            builder["field_cursor"] = _ACTION_SAVE
        elif n_custom > 0:
            ctx.layout_custom_cursor = n_custom - 1
        ctx.dirty = True
    elif name == "KEY_ENTER" or ch in ("\n", "\r"):
        if area == _AREA_SAVED and n_custom > 0:
            cl = custom_layouts[ctx.layout_custom_cursor]
            builder["name"] = cl.name
            builder["panes"] = cl.panes
            builder["direction"] = cl.direction
            builder["ratio"] = cl.ratio
            builder["message"] = f"Loaded '{cl.name}'"
            builder["area"] = _AREA_BUILDER
            builder["field_cursor"] = 0
        elif area == _AREA_BUILDER:
            fc = builder.get("field_cursor", 0)
            if fc < len(BUILDER_FIELDS):
                field_name = BUILDER_FIELDS[fc]
                if field_name == "direction":
                    builder["direction"] = "col" if builder.get("direction", "row") == "row" else "row"
                    builder["message"] = ""
                else:
                    builder["editing"] = True
                    builder["edit_buffer"] = str(builder.get(field_name, ""))
                    builder["message"] = ""
            elif fc == _ACTION_APPLY:
                _apply_custom_builder(ctx, builder)
            elif fc == _ACTION_SAVE:
                _save_custom_builder(ctx, builder, custom_layouts)
        ctx.dirty = True
    elif area == _AREA_BUILDER and len(ch) == 1 and ch.isprintable():
        fc = builder.get("field_cursor", 0)
        if fc < len(BUILDER_FIELDS):
            field_name = BUILDER_FIELDS[fc]
            if field_name != "direction":
                builder["editing"] = True
                builder["edit_buffer"] = ch
                builder["message"] = ""
        ctx.dirty = True
    elif ch == "d":
        if area == _AREA_SAVED and n_custom > 0 and ctx.layout_custom_cursor < n_custom:
            del custom_layouts[ctx.layout_custom_cursor]
            ctx.ws.cfg.custom_layouts = custom_layouts
            save_user_config(ctx.ws.cfg)
            ctx.layout_custom_cursor = max(0, min(ctx.layout_custom_cursor, len(custom_layouts) - 1))
            builder["message"] = "Layout deleted"
            ctx.dirty = True
    elif ch == "e":
        if area == _AREA_SAVED and n_custom > 0 and ctx.layout_custom_cursor < n_custom:
            cl = custom_layouts[ctx.layout_custom_cursor]
            builder["name"] = cl.name
            builder["panes"] = cl.panes
            builder["direction"] = cl.direction
            builder["ratio"] = cl.ratio
            builder["message"] = f"Loaded '{cl.name}'"
            builder["area"] = _AREA_BUILDER
            builder["field_cursor"] = 0
            ctx.dirty = True
    else:
        ctx.dirty = True


def _handle_editing(ch: str, name: str, ctx: AppContext, builder: dict) -> None:
    fc = builder.get("field_cursor", 0)
    field_name = BUILDER_FIELDS[fc]

    if name == "KEY_ENTER" or ch in ("\n", "\r"):
        _commit_edit(builder, field_name)
        builder["editing"] = False
        if fc < len(BUILDER_FIELDS) - 1:
            builder["field_cursor"] = fc + 1
        ctx.dirty = True
    elif name == "KEY_ESCAPE":
        builder["editing"] = False
        ctx.dirty = True
    elif name == "KEY_BACKSPACE" or ch == "\x7f" or ch == "\x08":
        buf = builder.get("edit_buffer", "")
        builder["edit_buffer"] = buf[:-1]
        ctx.dirty = True
    elif name in ("KEY_UP",):
        _commit_edit(builder, field_name)
        builder["editing"] = False
        if fc > 0:
            builder["field_cursor"] = fc - 1
            builder["editing"] = True
            new_field = BUILDER_FIELDS[builder["field_cursor"]]
            builder["edit_buffer"] = str(builder.get(new_field, ""))
        else:
            builder["area"] = _AREA_SAVED
        ctx.dirty = True
    elif name in ("KEY_DOWN",):
        _commit_edit(builder, field_name)
        builder["editing"] = False
        if fc < len(BUILDER_FIELDS) - 1:
            builder["field_cursor"] = fc + 1
            builder["editing"] = True
            new_field = BUILDER_FIELDS[builder["field_cursor"]]
            builder["edit_buffer"] = str(builder.get(new_field, ""))
        ctx.dirty = True
    elif len(ch) == 1 and ch.isprintable():
        builder["edit_buffer"] = builder.get("edit_buffer", "") + ch
        ctx.dirty = True
    else:
        ctx.dirty = True


def _commit_edit(builder: dict, field_name: str) -> None:
    raw = builder.get("edit_buffer", "")
    if field_name == "name":
        builder["name"] = raw
    elif field_name == "panes":
        try:
            val = int(raw)
            if 1 <= val <= 9:
                builder["panes"] = val
        except ValueError:
            pass
    elif field_name == "direction":
        if raw in ("row", "col"):
            builder["direction"] = raw
    elif field_name == "ratio":
        try:
            val = float(raw)
            if 0.1 <= val <= 0.9:
                builder["ratio"] = val
        except ValueError:
            pass


def _apply_custom_builder(ctx: AppContext, builder: dict) -> None:
    panes = builder.get("panes", 2)
    direction = builder.get("direction", "row")
    ratio = builder.get("ratio", 0.5)

    ctx.ws.apply_custom_layout(panes, direction, ratio)
    if ctx.send_remote_command:
        ctx.send_remote_command({
            "action": "apply_custom_layout",
            "panes": panes,
            "direction": direction,
            "ratio": ratio,
        })
    name_str = builder.get("name", "")
    builder["message"] = f"Applied{' ' + name_str if name_str else ''}"
    ctx.mode = "normal"
    ctx.dirty = True


def _save_custom_builder(ctx: AppContext, builder: dict, custom_layouts: list) -> None:
    layout_name = builder.get("name", "")
    if not layout_name:
        builder["message"] = "Error: name required"
        ctx.dirty = True
        return

    for i, cl in enumerate(custom_layouts):
        if cl.name == layout_name:
            custom_layouts[i] = CustomLayoutConfig(
                name=layout_name,
                panes=builder.get("panes", 2),
                direction=builder.get("direction", "row"),
                ratio=builder.get("ratio", 0.5),
            )
            ctx.ws.cfg.custom_layouts = custom_layouts
            save_user_config(ctx.ws.cfg)
            builder["message"] = f"Updated '{layout_name}'"
            ctx.dirty = True
            return

    custom_layouts.append(CustomLayoutConfig(
        name=layout_name,
        panes=builder.get("panes", 2),
        direction=builder.get("direction", "row"),
        ratio=builder.get("ratio", 0.5),
    ))
    ctx.ws.cfg.custom_layouts = custom_layouts
    save_user_config(ctx.ws.cfg)
    ctx.layout_custom_cursor = len(custom_layouts) - 1
    builder["message"] = f"Saved '{layout_name}'"
    ctx.dirty = True

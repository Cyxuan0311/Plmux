"""Session persistence: save/restore state to/from JSON files."""

from __future__ import annotations

import os
import sys
from typing import Any

from plmux.extensions.registry import ExtensionContext, emit_hook
from plmux.modes import AppContext
from plmux.session.models import tree_to_json
from plmux.session.store import save_session


def persist_session(ctx: AppContext, cfg: Any) -> None:
    buffer_dumps: dict[str, str] = {}
    sessions_data: list[dict] = []
    global_idx = 0
    for sess in ctx.ws.sessions_list:
        pane_offset = global_idx
        for w in sess.windows:
            for s in w.panes:
                try:
                    buffer_dumps[str(global_idx)] = s.dump_buffer()
                except Exception:
                    pass
                global_idx += 1
        windows_data = []
        for w in sess.windows:
            windows_data.append({
                "tree": tree_to_json(w.tree),
                "focus_pane": w.focus_pane,
            })
        sessions_data.append({
            "name": sess.name,
            "windows": windows_data,
            "current_window": sess.current_window,
            "pane_offset": pane_offset,
            "pane_count": global_idx - pane_offset,
        })
    save_session(
        cfg,
        tree=ctx.ws.tree,
        focus_pane=ctx.ws.focus_pane,
        shell=cfg.shell,
        cwd=os.getcwd(),
        extra_meta={"argv0": sys.argv[0], "theme": ctx.ws.theme.name},
        buffer_dumps=buffer_dumps,
        sessions_data=sessions_data,
        current_session=ctx.ws.current_session,
    )
    emit_hook("session_saved", ExtensionContext(hook_name="session_saved"))

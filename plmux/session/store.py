"""JSON persistence for layout (session restore is best-effort)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from plmux.config.loader import default_user_config_dir
from plmux.config.schema import PlmuxConfig
from plmux.session.models import SessionSnapshot, tree_to_json


def resolve_state_path(cfg: PlmuxConfig) -> Path:
    if cfg.session.state_path:
        return Path(cfg.session.state_path).expanduser()
    return default_user_config_dir() / "session.json"


def save_session(
    cfg: PlmuxConfig,
    *,
    tree: Any,
    focus_pane: int,
    shell: list[str] | None,
    cwd: str | None,
    extra_meta: Dict[str, Any] | None = None,
    buffer_dumps: Dict[str, str] | None = None,
) -> None:
    if not cfg.session.auto_save:
        return
    path = resolve_state_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    snap = SessionSnapshot(
        tree=tree_to_json(tree),
        focus_pane=focus_pane,
        shell=list(shell) if shell else None,
        cwd=cwd,
        meta=dict(extra_meta or {}),
        buffer_dumps=dict(buffer_dumps) if buffer_dumps else None,
    )
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(snap.to_json(), f, indent=2, ensure_ascii=False)
    tmp.replace(path)


def load_session(cfg: PlmuxConfig) -> SessionSnapshot | None:
    path = resolve_state_path(cfg)
    if not path.is_file():
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    snap = SessionSnapshot.from_json(data)
    if snap.version != 1:
        # Future: migrate based on version
        pass
    return snap

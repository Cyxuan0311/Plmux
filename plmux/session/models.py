"""Serializable session snapshot (versioned for future migrations)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Union

Tree = Union[int, List[Any]]


@dataclass
class SessionSnapshot:
    version: int = 1
    tree: Tree = 0
    focus_pane: int = 0
    shell: Optional[List[str]] = None
    cwd: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)
    buffer_dumps: Optional[Dict[str, str]] = None

    def to_json(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

    @staticmethod
    def from_json(d: Dict[str, Any]) -> "SessionSnapshot":
        return SessionSnapshot(
            version=int(d.get("version", 1)),
            tree=d.get("tree", 0),
            focus_pane=int(d.get("focus_pane", 0)),
            shell=d.get("shell"),
            cwd=d.get("cwd"),
            meta=dict(d.get("meta") or {}),
            buffer_dumps=dict(d.get("buffer_dumps") or {}),
        )


def tree_to_json(tree: Any) -> Tree:
    if isinstance(tree, int):
        return tree
    d, r, a, b = tree
    return [d, r, tree_to_json(a), tree_to_json(b)]


def tree_from_json(t: Tree) -> Any:
    if isinstance(t, int):
        return t
    if isinstance(t, list) and len(t) >= 3:
        d = str(t[0])
        if len(t) == 4:
            r = float(t[1])
            a = tree_from_json(t[2])
            b = tree_from_json(t[3])
        else:
            r = 0.5
            a = tree_from_json(t[1])
            b = tree_from_json(t[2])
        return (d, r, a, b)
    return 0
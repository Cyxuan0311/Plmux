"""Daemon state: data classes and serialization."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List

from plmux.session.models import tree_to_json, tree_from_json


@dataclass
class SessionHandle:
    index: int
    fd: int
    pid: int
    rows: int
    cols: int
    argv: List[str]


@dataclass
class ServerState:
    tree: Any = 0
    focus_pane: int = 0
    sessions: List[SessionHandle] = field(default_factory=list)
    session_count: int = 0
    windows: List[Dict[str, Any]] = field(default_factory=list)
    current_window: int = 0
    buffer_dumps: Dict[str, str] = field(default_factory=dict)
    sessions_data: List[Dict[str, Any]] = field(default_factory=list)
    current_session: int = 0


def serialize_state(state: ServerState) -> bytes:
    data: Dict[str, Any] = {
        "tree": tree_to_json(state.tree),
        "focus_pane": state.focus_pane,
        "session_count": state.session_count,
        "sessions": [
            {
                "index": s.index,
                "rows": s.rows,
                "cols": s.cols,
                "pid": s.pid,
                "argv": s.argv,
            }
            for s in state.sessions
        ],
        "windows": state.windows,
        "current_window": state.current_window,
        "buffer_dumps": state.buffer_dumps,
        "sessions_data": state.sessions_data,
        "current_session": state.current_session,
    }
    return json.dumps(data).encode("utf-8")


def deserialize_state(raw: bytes) -> ServerState:
    data = json.loads(raw.decode("utf-8"))
    sessions = [
        SessionHandle(
            index=s["index"],
            fd=-1,
            pid=s["pid"],
            rows=s["rows"],
            cols=s["cols"],
            argv=s["argv"],
        )
        for s in data["sessions"]
    ]
    return ServerState(
        tree=tree_from_json(data["tree"]),
        focus_pane=data["focus_pane"],
        sessions=sessions,
        session_count=data["session_count"],
        windows=data.get("windows", []),
        current_window=data.get("current_window", 0),
        buffer_dumps=data.get("buffer_dumps", {}),
        sessions_data=data.get("sessions_data", []),
        current_session=data.get("current_session", 0),
    )

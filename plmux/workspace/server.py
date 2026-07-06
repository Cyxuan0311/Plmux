from __future__ import annotations

from typing import Callable, Dict, List, Optional

from plmux.config.schema import PlmuxConfig
from plmux.extensions.registry import ExtensionContext, emit_hook
from plmux.session.models import SessionSnapshot, tree_from_json
from plmux.terminal.session import TerminalSession
from plmux.ui.geometry import Tree, count_panes
from plmux.ui.theme import Theme
from plmux.buffer.manager import BufferManager

from plmux.workspace.session import Session
from plmux.workspace.window import Window


class TmuxServer:
    """Top-level server: manages multiple sessions.

    Delegates window/pane operations to the current session so that
    ``ctx.ws`` continues to work as before (``ws.split()``, ``ws.tree``,
    ``ws.focus_pane``, etc.).
    """

    def __init__(
        self,
        cfg: PlmuxConfig,
        theme: Theme,
        *,
        on_dirty: Optional[Callable[[], None]] = None,
        restore: Optional[SessionSnapshot] = None,
    ) -> None:
        self.cfg = cfg
        self.theme = theme
        self._on_dirty = on_dirty

        def mark() -> None:
            if self._on_dirty:
                self._on_dirty()

        self._mark = mark
        self.sessions_list: List[Session] = []
        self.current_session: int = 0
        self.web_mode: str = "normal"
        self.web_cmd_buffer: str = ""
        self.clock_mode_pane: int | None = None
        self.clock_str: str = ""
        self._web_term_rows: int | None = None
        self._web_term_cols: int | None = None
        self._overlay_cols: int = 80
        self._overlay_rows: int = 26
        self.buffers: BufferManager = BufferManager()

        if restore and restore.sessions_data:
            for sd in restore.sessions_data:
                from plmux.session.models import SessionSnapshot
                win_data = sd.get("windows", [])
                if win_data:
                    first_win = win_data[0]
                    snap = SessionSnapshot(
                        tree=first_win.get("tree", 0),
                        focus_pane=first_win.get("focus_pane", 0),
                        buffer_dumps=restore.buffer_dumps,
                    )
                else:
                    snap = None
                sess = Session(cfg, theme, mark, self._make_session, name=sd.get("name", ""), restore=snap)
                if win_data and len(win_data) > 1:
                    for w_data in win_data[1:]:
                        w_tree = tree_from_json(w_data.get("tree", 0))
                        n_panes = count_panes(w_tree)
                        w_panes = [self._make_session(24, 80, shell=cfg.shell, env=cfg.env) for _ in range(n_panes)]
                        if restore.buffer_dumps:
                            for key, encoded in restore.buffer_dumps.items():
                                try:
                                    bidx = int(key)
                                except (ValueError, TypeError):
                                    continue
                                if 0 <= bidx < len(w_panes):
                                    w_panes[bidx].restore_buffer(encoded)
                        sess.windows.append(Window(tree=w_tree, focus_pane=max(0, min(w_data.get("focus_pane", 0), n_panes - 1)), panes=w_panes))
                sess.current_window = sd.get("current_window", 0)
                self.sessions_list.append(sess)
            self.current_session = min(restore.current_session, len(self.sessions_list) - 1)
        else:
            sess = Session(cfg, theme, mark, self._make_session, restore=restore)
            self.sessions_list.append(sess)

    def _make_session(
        self,
        rows: int,
        cols: int,
        *,
        shell: Optional[list[str]] = None,
        env: Optional[dict] = None,
    ) -> TerminalSession:
        s = TerminalSession(
            rows,
            cols,
            shell=shell if shell is not None else self.cfg.shell,
            env=env if env is not None else self.cfg.env,
            on_update=self._mark,
            scrollback_lines=self.cfg.ui.scrollback_lines,
        )
        return s

    # ── current session access ─────────────────────────────────────

    def _session(self) -> Session:
        return self.sessions_list[self.current_session]

    # ── delegated properties (current session) ─────────────────────

    @property
    def windows(self) -> List[Window]:
        return self._session().windows

    @windows.setter
    def windows(self, value: List[Window]) -> None:
        self._session().windows = value

    @property
    def current_window(self) -> int:
        return self._session().current_window

    @current_window.setter
    def current_window(self, value: int) -> None:
        self._session().current_window = value

    @property
    def session_name(self) -> str:
        return self._session().name

    @session_name.setter
    def session_name(self, value: str) -> None:
        self._session().name = value

    @property
    def sessions(self) -> List[TerminalSession]:
        return self._session().sessions

    @property
    def tree(self) -> Tree:
        return self._session().tree

    @tree.setter
    def tree(self, value: Tree) -> None:
        self._session().tree = value

    @property
    def focus_pane(self) -> int:
        return self._session().focus_pane

    @focus_pane.setter
    def focus_pane(self, value: int) -> None:
        self._session().focus_pane = value

    @property
    def zoom_pane(self) -> int | None:
        return self._session().zoom_pane

    @zoom_pane.setter
    def zoom_pane(self, value: int | None) -> None:
        self._session().zoom_pane = value

    def _window(self) -> Window:
        return self._session()._window()

    # ── delegated methods (current session) ────────────────────────

    def split(self, direction: str) -> None:
        self._session().split(direction)

    def resize_pane(self, direction: str) -> None:
        self._session().resize_pane(direction)

    def only_pane(self) -> None:
        self._session().only_pane()

    def remove_pane(self, idx: int) -> bool:
        return self._session().remove_pane(idx)

    def focus_next(self) -> None:
        self._session().focus_next()

    def focus_prev(self) -> None:
        self._session().focus_prev()

    def focus_direction(self, direction: str) -> None:
        self._session().focus_direction(direction)

    def swap_pane(self, direction: str) -> None:
        self._session().swap_pane(direction)

    def break_pane(self, pane_idx: int | None = None) -> bool:
        return self._session().break_pane(pane_idx)

    def join_pane(self, direction: str = "row") -> bool:
        return self._session().join_pane(direction)

    def respawn_pane(self, pane_idx: int | None = None) -> bool:
        return self._session().respawn_pane(pane_idx)

    def send_keys(self, text: str) -> None:
        self._session().send_keys(text)

    def toggle_zoom(self) -> None:
        self._session().toggle_zoom()

    def rotate_panes(self, direction: str = "up") -> None:
        self._session().rotate_panes(direction)

    def sync_geometry(self, content_rows: int, content_cols: int) -> None:
        rows = self._web_term_rows if self._web_term_rows is not None else content_rows
        cols = self._web_term_cols if self._web_term_cols is not None else content_cols
        self._session().sync_geometry(rows, cols)

    def active_session(self) -> TerminalSession:
        return self._session().active_session()

    def set_focus_pane(self, n: int) -> bool:
        return self._session().set_focus_pane(n)

    def pane_title(self, idx: int) -> str:
        return self._session().pane_title(idx)

    def setenv(self, key: str, value: str) -> None:
        self._session().setenv(key, value)

    def unsetenv(self, key: str) -> bool:
        return self._session().unsetenv(key)

    def showenv(self) -> Dict[str, str]:
        return self._session().showenv()

    def new_window(self) -> None:
        self._session().new_window()

    def close_window(self) -> bool:
        return self._session().close_window()

    def close_window_by_index(self, win_idx: int) -> bool:
        return self._session().close_window_by_index(win_idx)

    def next_window(self) -> None:
        self._session().next_window()

    def prev_window(self) -> None:
        self._session().prev_window()

    def last_window(self) -> None:
        self._session().last_window()

    def last_pane(self) -> None:
        self._session().last_pane()

    def goto_window(self, n: int) -> bool:
        return self._session().goto_window(n)

    def rename_window(self, name: str) -> None:
        self._session().rename_window(name)

    def cycle_layout(self) -> None:
        self._session().cycle_layout()

    def apply_layout_template(self, template_name: str) -> bool:
        return self._session().apply_layout_template(template_name)

    def apply_custom_layout(self, panes: int, direction: str = "row", ratio: float = 0.5) -> bool:
        return self._session().apply_custom_layout(panes, direction, ratio)

    def shutdown(self) -> None:
        for sess in self.sessions_list:
            sess.shutdown()

    # ── session management ─────────────────────────────────────────

    def new_session(self, name: str = "") -> Session:
        sess = Session(self.cfg, self.theme, self._mark, self._make_session, name=name)
        self.sessions_list.append(sess)
        self.current_session = len(self.sessions_list) - 1
        self._mark()
        emit_hook("session_created", ExtensionContext(hook_name="session_created", session_index=self.current_session))
        return sess

    def kill_session(self, idx: int | None = None) -> bool:
        if len(self.sessions_list) <= 1:
            return False
        if idx is None:
            idx = self.current_session
        if idx < 0 or idx >= len(self.sessions_list):
            return False
        emit_hook("session_killed", ExtensionContext(hook_name="session_killed", session_index=idx))
        self.sessions_list[idx].shutdown()
        del self.sessions_list[idx]
        if self.current_session >= len(self.sessions_list):
            self.current_session = len(self.sessions_list) - 1
        self._mark()
        return True

    def switch_session(self, idx: int) -> bool:
        if 0 <= idx < len(self.sessions_list):
            self.current_session = idx
            self._mark()
            return True
        return False

    def next_session(self) -> None:
        if len(self.sessions_list) <= 1:
            return
        self.current_session = (self.current_session + 1) % len(self.sessions_list)
        self._mark()

    def prev_session(self) -> None:
        if len(self.sessions_list) <= 1:
            return
        self.current_session = (self.current_session - 1) % len(self.sessions_list)
        self._mark()

    def rename_session(self, name: str) -> None:
        self._session().name = name
        self._mark()

    def find_session(self, name: str) -> int:
        for i, s in enumerate(self.sessions_list):
            if s.name == name:
                return i
        return -1

    def all_sessions(self) -> List[Session]:
        return self.sessions_list

    def all_panes(self) -> List[TerminalSession]:
        out: List[TerminalSession] = []
        for sess in self.sessions_list:
            out.extend(sess.sessions)
        return out

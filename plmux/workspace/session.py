from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional

from plmux.config.schema import PlmuxConfig
from plmux.extensions.registry import ExtensionContext, emit_hook
from plmux.session.models import SessionSnapshot, tree_from_json
from plmux.terminal.session import TerminalSession
from plmux.ui.geometry import (
    Tree,
    adjust_ratio,
    assign_rects,
    count_panes,
    pane_indices,
    reindex_after_remove,
    remove_pane_collapse,
    replace_pane,
    rotate_leaves,
)
from plmux.ui.theme import Theme

from plmux.workspace.layouts import (
    LAYOUT_CYCLE,
    LAYOUT_TEMPLATES,
    build_custom_tree,
    build_layout,
    build_template_tree,
)
from plmux.workspace.navigation import direction_score
from plmux.workspace.snapshot import reindex_tree
from plmux.workspace.window import Window


class Session:
    """A tmux session: owns windows, each window owns panes."""

    def __init__(
        self,
        cfg: PlmuxConfig,
        theme: Theme,
        mark: Callable[[], None],
        make_session: Callable,
        *,
        name: str = "",
        restore: Optional[SessionSnapshot] = None,
    ) -> None:
        self.cfg = cfg
        self.theme = theme
        self._mark = mark
        self._make_session = make_session
        self.name: str = name
        self.env: Dict[str, str] = dict(cfg.env)
        self.windows: List[Window] = []
        self.current_window: int = 0
        self.zoom_pane: int | None = None
        self._zoomed: bool = False
        self._zoom_prev_tree: Tree | None = None
        self._zoom_prev_focus: int | None = None
        self._last_window: int = 0
        self._last_pane: int = 0
        self._content_rows: int | None = None
        self._content_cols: int | None = None

        if restore:
            tree = tree_from_json(restore.tree)
            n = count_panes(tree)
            shell = restore.shell if restore.shell is not None else cfg.shell
            panes: List[TerminalSession] = []
            for _ in range(n):
                panes.append(make_session(24, 80, shell=shell, env=cfg.env))
            if restore.buffer_dumps:
                for key, encoded in restore.buffer_dumps.items():
                    try:
                        idx = int(key)
                    except (ValueError, TypeError):
                        continue
                    if 0 <= idx < len(panes):
                        panes[idx].restore_buffer(encoded)
            self.windows.append(Window(tree=tree, focus_pane=max(0, min(restore.focus_pane, n - 1)), panes=panes))
        else:
            pane0 = make_session(24, 80, shell=cfg.shell, env=cfg.env)
            self.windows.append(Window(tree=0, focus_pane=0, panes=[pane0]))

    @property
    def sessions(self) -> List[TerminalSession]:
        out: List[TerminalSession] = []
        for w in self.windows:
            out.extend(w.panes)
        return out

    @property
    def tree(self) -> Tree:
        return self.windows[self.current_window].tree

    @tree.setter
    def tree(self, value: Tree) -> None:
        self.windows[self.current_window].tree = value

    @property
    def focus_pane(self) -> int:
        return self.windows[self.current_window].focus_pane

    @focus_pane.setter
    def focus_pane(self, value: int) -> None:
        self.windows[self.current_window].focus_pane = value

    def _window(self) -> Window:
        return self.windows[self.current_window]

    def split(self, direction: str) -> None:
        win = self._window()
        new_session = self._make_session(24, 80, shell=self.cfg.shell, env=self.env)
        new_idx = len(win.panes)
        win.panes.append(new_session)
        sub: Tree = (direction, 0.5, self.focus_pane, new_idx)
        win.tree = replace_pane(win.tree, self.focus_pane, sub)
        win.focus_pane = new_idx
        self._mark()
        emit_hook("pane_created", ExtensionContext(hook_name="pane_created", pane_index=new_idx))

    def resize_pane(self, direction: str) -> None:
        win = self._window()
        new_tree = adjust_ratio(win.tree, win.focus_pane, direction)
        if new_tree is not None:
            win.tree = new_tree
            self._mark()

    def only_pane(self) -> None:
        win = self._window()
        indices = pane_indices(win.tree)
        keep_idx = win.focus_pane
        keep_session = win.panes[keep_idx] if 0 <= keep_idx < len(win.panes) else None
        for idx in sorted(indices, reverse=True):
            if idx != keep_idx:
                emit_hook("pane_closed", ExtensionContext(hook_name="pane_closed", pane_index=idx))
                if 0 <= idx < len(win.panes):
                    win.panes[idx].close()
        win.panes = [keep_session] if keep_session else []
        win.tree = 0
        win.focus_pane = 0
        self._mark()

    def remove_pane(self, idx: int) -> bool:
        win = self._window()
        if idx < 0 or idx >= len(win.panes):
            return True

        emit_hook("pane_closed", ExtensionContext(hook_name="pane_closed", pane_index=idx))

        if len(win.panes) <= 1:
            win.panes[idx].close()
            win.panes = []
            win.tree = 0
            win.focus_pane = 0
            self._mark()
            return False

        win.panes[idx].close()
        del win.panes[idx]

        new_tree = remove_pane_collapse(win.tree, idx)
        if new_tree is None:
            win.tree = 0
        else:
            win.tree = reindex_after_remove(new_tree, idx)
        if win.focus_pane > idx:
            win.focus_pane -= 1
        elif win.focus_pane == idx:
            order = pane_indices(win.tree)
            win.focus_pane = order[0] if order else 0
        win.focus_pane = max(0, min(win.focus_pane, count_panes(win.tree) - 1))

        self._mark()
        return True

    def focus_next(self) -> None:
        win = self._window()
        order = pane_indices(win.tree)
        if len(order) <= 1:
            return
        if win.focus_pane not in order:
            win.focus_pane = order[0]
            return
        self._last_pane = win.focus_pane
        pos = order.index(win.focus_pane)
        win.focus_pane = order[(pos + 1) % len(order)]
        self._mark()

    def focus_prev(self) -> None:
        win = self._window()
        order = pane_indices(win.tree)
        if len(order) <= 1:
            return
        if win.focus_pane not in order:
            win.focus_pane = order[0]
            return
        self._last_pane = win.focus_pane
        pos = order.index(win.focus_pane)
        win.focus_pane = order[(pos - 1) % len(order)]
        self._mark()

    def toggle_zoom(self) -> None:
        win = self._window()
        if not self._zoomed:
            self._zoom_prev_tree = win.tree
            self._zoom_prev_focus = win.focus_pane
            self.zoom_pane = win.focus_pane
            self._zoomed = True
        else:
            if self._zoom_prev_tree is not None:
                win.tree = self._zoom_prev_tree
            if self._zoom_prev_focus is not None:
                win.focus_pane = self._zoom_prev_focus
            self.zoom_pane = None
            self._zoomed = False
        self._mark()

    def rotate_panes(self, direction: str = "up") -> None:
        win = self._window()
        indices = pane_indices(win.tree)
        if len(indices) <= 1:
            return
        win.tree = rotate_leaves(win.tree, direction)
        self._mark()

    def focus_direction(self, direction: str) -> None:
        win = self._window()
        rects = assign_rects(win.tree, 0, 0, self._content_rows or 24, self._content_cols or 80)
        if len(rects) <= 1:
            return
        if win.focus_pane not in rects:
            return
        cur = rects[win.focus_pane]
        best_idx = None
        best_score = float("inf")
        for idx, r in rects.items():
            if idx == win.focus_pane:
                continue
            score = direction_score(cur, r, direction)
            if score is not None and score < best_score:
                best_score = score
                best_idx = idx
        if best_idx is not None:
            win.focus_pane = best_idx
            self._mark()

    def swap_pane(self, direction: str) -> None:
        win = self._window()
        order = pane_indices(win.tree)
        if len(order) <= 1:
            return
        pos = order.index(win.focus_pane)
        if direction == "up":
            target_pos = (pos + 1) % len(order)
        else:
            target_pos = (pos - 1) % len(order)
        target_idx = order[target_pos]
        mapping = {order[pos]: order[target_pos], order[target_pos]: order[pos]}

        def _remap(t: Tree) -> Tree:
            if isinstance(t, int):
                return mapping.get(t, t)
            d, r, a, b = t
            return (d, r, _remap(a), _remap(b))

        win.tree = _remap(win.tree)
        win.focus_pane = target_idx
        self._mark()

    def break_pane(self, pane_idx: int | None = None) -> bool:
        win = self._window()
        if len(win.panes) <= 1:
            return False
        idx = pane_idx if pane_idx is not None else win.focus_pane
        if idx < 0 or idx >= len(win.panes):
            return False
        pane_session = win.panes[idx]
        emit_hook("pane_closed", ExtensionContext(hook_name="pane_closed", pane_index=idx))
        del win.panes[idx]
        new_tree = remove_pane_collapse(win.tree, idx)
        if new_tree is None:
            win.tree = 0
        else:
            win.tree = reindex_after_remove(new_tree, idx)
        if win.focus_pane > idx:
            win.focus_pane -= 1
        elif win.focus_pane == idx:
            order = pane_indices(win.tree)
            win.focus_pane = order[0] if order else 0
        win.focus_pane = max(0, min(win.focus_pane, count_panes(win.tree) - 1))
        new_win = Window(tree=0, focus_pane=0, panes=[pane_session])
        self.windows.append(new_win)
        self.current_window = len(self.windows) - 1
        self._mark()
        emit_hook("window_created", ExtensionContext(hook_name="window_created", window_index=self.current_window, pane_index=0))
        return True

    def join_pane(self, direction: str = "row") -> bool:
        if len(self.windows) <= 1:
            return False
        src_win_idx = (self.current_window + 1) % len(self.windows)
        src_win = self.windows[src_win_idx]
        if not src_win.panes:
            return False
        last_pane_idx = len(src_win.panes) - 1
        pane_to_move = src_win.panes[last_pane_idx]
        del src_win.panes[last_pane_idx]
        if src_win.panes:
            src_new_tree = remove_pane_collapse(src_win.tree, last_pane_idx)
            if src_new_tree is None:
                src_win.tree = 0
            else:
                src_win.tree = reindex_after_remove(src_new_tree, last_pane_idx)
        else:
            src_win.tree = 0
        win = self._window()
        new_idx = len(win.panes)
        win.panes.append(pane_to_move)
        sub: Tree = (direction, 0.5, self.focus_pane, new_idx)
        win.tree = replace_pane(win.tree, self.focus_pane, sub)
        win.focus_pane = new_idx
        self._mark()
        emit_hook("pane_created", ExtensionContext(hook_name="pane_created", pane_index=new_idx))
        return True

    def respawn_pane(self, pane_idx: int | None = None) -> bool:
        win = self._window()
        idx = pane_idx if pane_idx is not None else win.focus_pane
        if idx < 0 or idx >= len(win.panes):
            return False
        old_argv = win.panes[idx].argv
        old_env = dict(self.env)
        old_rows = win.panes[idx].rows
        old_cols = win.panes[idx].cols
        on_update_cb = getattr(win.panes[idx], "_on_update", None)
        win.panes[idx].close()
        new_sess = TerminalSession(
            max(1, old_rows),
            max(1, old_cols),
            shell=list(old_argv),
            env=old_env,
            on_update=on_update_cb,
            scrollback_lines=self.cfg.ui.scrollback_lines,
        )
        win.panes[idx] = new_sess
        self._mark()
        return True

    def send_keys(self, text: str) -> None:
        s = self.active_session()
        s.write_text(text)

    def sync_geometry(self, content_rows: int, content_cols: int) -> None:
        self._content_rows = content_rows
        self._content_cols = content_cols
        win = self._window()
        total_rows = max(self.cfg.ui.min_pane_rows, content_rows)
        total_cols = max(self.cfg.ui.min_pane_cols, content_cols)
        rects = assign_rects(win.tree, 0, 0, total_rows, total_cols)

        for idx, r in rects.items():
            if 0 <= idx < len(win.panes):
                new_rows = max(self.cfg.ui.min_pane_rows, r.rows - 2)
                new_cols = max(self.cfg.ui.min_pane_cols, r.cols - 2)
                old_rows = win.panes[idx].rows
                old_cols = win.panes[idx].cols
                if new_rows != old_rows or new_cols != old_cols:
                    win.panes[idx].resize(new_rows, new_cols)

    def active_session(self) -> TerminalSession:
        win = self._window()
        if win.focus_pane < len(win.panes):
            return win.panes[win.focus_pane]
        return win.panes[0]

    def set_focus_pane(self, n: int) -> bool:
        win = self._window()
        if 0 <= n < len(win.panes):
            old = win.focus_pane
            win.focus_pane = n
            self._mark()
            if old != n:
                emit_hook("pane_focus_changed", ExtensionContext(hook_name="pane_focus_changed", pane_index=n, message=str(old)))
            return True
        return False

    def pane_title(self, idx: int) -> str:
        win = self._window()
        s = win.panes[idx]
        cwd = None
        if sys.platform != "win32" and os.name != "nt" and s.proc is not None:
            try:
                cwd = os.readlink(f"/proc/{s.proc.pid}/cwd")
            except OSError:
                pass
        else:
            try:
                cwd = os.getcwd()
            except OSError:
                pass
        if cwd is None:
            name = Path(s.argv[0]).name if s.argv else "shell"
            return f"{idx}:{name}"
        max_len = max(10, s.cols // 2)
        if len(cwd) <= max_len:
            return cwd
        half = (max_len - 3) // 2
        return cwd[:half] + "..." + cwd[-half:]

    def shutdown(self) -> None:
        for w in self.windows:
            for s in w.panes:
                s.close()

    def new_window(self) -> None:
        pane0 = self._make_session(24, 80, shell=self.cfg.shell, env=self.env)
        self.windows.append(Window(tree=0, focus_pane=0, panes=[pane0]))
        self.current_window = len(self.windows) - 1
        self._mark()
        emit_hook("window_created", ExtensionContext(hook_name="window_created", window_index=self.current_window, pane_index=0))

    def close_window(self) -> bool:
        if len(self.windows) <= 1:
            return False
        win_idx = self.current_window
        return self.close_window_by_index(win_idx)

    def close_window_by_index(self, win_idx: int) -> bool:
        if win_idx < 0 or win_idx >= len(self.windows):
            return False
        if len(self.windows) <= 1:
            return False
        emit_hook("window_closed", ExtensionContext(hook_name="window_closed", window_index=win_idx))
        win = self.windows[win_idx]
        for s in win.panes:
            s.close()
        del self.windows[win_idx]
        if self.current_window >= len(self.windows):
            self.current_window = len(self.windows) - 1
        self._mark()
        return True

    def next_window(self) -> None:
        if len(self.windows) <= 1:
            return
        self._last_window = self.current_window
        self.current_window = (self.current_window + 1) % len(self.windows)
        self._mark()

    def prev_window(self) -> None:
        if len(self.windows) <= 1:
            return
        self._last_window = self.current_window
        self.current_window = (self.current_window - 1) % len(self.windows)
        self._mark()

    def goto_window(self, n: int) -> bool:
        if 0 <= n < len(self.windows):
            self._last_window = self.current_window
            self.current_window = n
            self._mark()
            return True
        return False

    def last_window(self) -> None:
        if len(self.windows) <= 1:
            return
        prev = self._last_window
        self._last_window = self.current_window
        self.current_window = prev
        self._mark()

    def last_pane(self) -> None:
        win = self._window()
        prev = self._last_pane
        order = pane_indices(win.tree)
        if prev not in order:
            return
        self._last_pane = win.focus_pane
        win.focus_pane = prev
        self._mark()

    def rename_window(self, name: str) -> None:
        self.windows[self.current_window].name = name
        self._mark()

    def cycle_layout(self) -> None:
        win = self._window()
        panes = pane_indices(win.tree)
        n = len(panes)
        if n <= 1:
            return

        current_name = self._detect_layout_name()
        try:
            idx = LAYOUT_CYCLE.index(current_name)
            next_name = LAYOUT_CYCLE[(idx + 1) % len(LAYOUT_CYCLE)]
        except ValueError:
            next_name = LAYOUT_CYCLE[0]

        new_tree = build_layout(panes, next_name)
        if new_tree is not None:
            win.tree = new_tree
            self._mark()

    def _detect_layout_name(self) -> str:
        win = self._window()
        panes = pane_indices(win.tree)
        n = len(panes)
        if n <= 1:
            return "even"
        if isinstance(win.tree, int):
            return "even"
        return "even"

    def setenv(self, key: str, value: str) -> None:
        self.env[key] = value

    def unsetenv(self, key: str) -> bool:
        if key in self.env:
            del self.env[key]
            return True
        return False

    def showenv(self) -> Dict[str, str]:
        return dict(self.env)

    def apply_layout_template(self, template_name: str) -> bool:
        tpl = None
        for t in LAYOUT_TEMPLATES:
            if t.name == template_name:
                tpl = t
                break

        from plmux.extensions.registry import get_layout_algorithm
        plugin_algo = get_layout_algorithm(template_name)

        if tpl is None and plugin_algo is None:
            return False

        win = self._window()
        current_indices = pane_indices(win.tree)
        current_n = len(current_indices)
        needed = tpl.min_panes if tpl else 1

        while current_n < needed:
            win.panes.append(self._make_session(24, 80, shell=self.cfg.shell, env=self.env))
            current_n = len(win.panes)

        all_indices = list(range(current_n))
        new_tree = build_template_tree(all_indices, template_name)
        if new_tree is None:
            return False

        used_indices = set(pane_indices(new_tree))
        unused = sorted([i for i in all_indices if i not in used_indices], reverse=True)
        for idx in unused:
            if 0 <= idx < len(win.panes):
                win.panes[idx].close()
                emit_hook("pane_closed", ExtensionContext(hook_name="pane_closed", pane_index=idx))
        if unused:
            win.panes = [s for i, s in enumerate(win.panes) if i not in set(unused)]
            new_tree = reindex_tree(new_tree, unused)

        win.tree = new_tree
        win.focus_pane = 0
        self._mark()
        return True

    def apply_custom_layout(self, panes: int, direction: str = "row", ratio: float = 0.5) -> bool:
        if panes < 1:
            return False
        ratio = max(0.1, min(0.9, ratio))
        win = self._window()
        current_n = len(win.panes)
        while current_n < panes:
            win.panes.append(self._make_session(24, 80, shell=self.cfg.shell, env=self.env))
            current_n = len(win.panes)
        all_indices = list(range(current_n))
        new_tree = build_custom_tree(all_indices[:panes], direction, ratio)
        unused = sorted(all_indices[panes:], reverse=True)
        for idx in unused:
            if 0 <= idx < len(win.panes):
                win.panes[idx].close()
                emit_hook("pane_closed", ExtensionContext(hook_name="pane_closed", pane_index=idx))
        if unused:
            win.panes = [s for i, s in enumerate(win.panes) if i not in set(unused)]
            new_tree = reindex_tree(new_tree, unused)
        win.tree = new_tree
        win.focus_pane = 0
        self._mark()
        return True

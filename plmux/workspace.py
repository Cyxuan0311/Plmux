"""Pane tree + PTY sessions (resize, split, focus, windows, layouts)."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
import sys
from pathlib import Path
from typing import Callable, List, Optional

from plmux.config.schema import PlmuxConfig
from plmux.session.models import SessionSnapshot, tree_from_json
from plmux.session.store import load_session
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
)
from plmux.ui.theme import Theme
from plmux.extensions.registry import ExtensionContext, emit_hook


def _reindex_tree(tree: Tree, removed_indices: list[int]) -> Tree:
    if not removed_indices:
        return tree
    removed_set = set(removed_indices)
    all_idx = pane_indices(tree)
    max_idx = max(max(all_idx), max(removed_set)) if all_idx else 0
    mapping: dict[int, int] = {}
    shift = 0
    for i in range(max_idx + 2):
        if i in removed_set:
            shift += 1
        else:
            mapping[i] = i - shift
    if isinstance(tree, int):
        return mapping.get(tree, tree)
    d, r, a, b = tree
    return (d, r, _reindex_tree(a, removed_indices), _reindex_tree(b, removed_indices))


@dataclass
class Window:
    tree: Tree = 0
    focus_pane: int = 0


LAYOUT_CYCLE = [
    "even",
    "main-vertical",
    "main-horizontal",
]


@dataclass
class LayoutTemplate:
    name: str
    description: str
    min_panes: int
    ascii_preview: list[str]


LAYOUT_TEMPLATES: list[LayoutTemplate] = [
    LayoutTemplate(
        name="even-horizontal",
        description="Even horizontal split",
        min_panes=2,
        ascii_preview=[
            "┌──────┬──────┐",
            "│      │      │",
            "│  P1  │  P2  │",
            "│      │      │",
            "└──────┴──────┘",
        ],
    ),
    LayoutTemplate(
        name="even-vertical",
        description="Even vertical split",
        min_panes=2,
        ascii_preview=[
            "┌────────────┐",
            "│     P1     │",
            "├────────────┤",
            "│     P2     │",
            "└────────────┘",
        ],
    ),
    LayoutTemplate(
        name="main-vertical",
        description="Main left + stack right",
        min_panes=3,
        ascii_preview=[
            "┌────────┬─────┐",
            "│        │ P2  │",
            "│  Main  ├─────┤",
            "│        │ P3  │",
            "└────────┴─────┘",
        ],
    ),
    LayoutTemplate(
        name="main-horizontal",
        description="Main top + stack bottom",
        min_panes=3,
        ascii_preview=[
            "┌────────────┐",
            "│    Main    │",
            "├──────┬─────┤",
            "│  P2  │ P3  │",
            "└──────┴─────┘",
        ],
    ),
    LayoutTemplate(
        name="quad",
        description="2x2 grid",
        min_panes=4,
        ascii_preview=[
            "┌──────┬──────┐",
            "│  P1  │  P2  │",
            "├──────┼──────┤",
            "│  P3  │  P4  │",
            "└──────┴──────┘",
        ],
    ),
    LayoutTemplate(
        name="columns",
        description="Three equal columns",
        min_panes=3,
        ascii_preview=[
            "┌────┬────┬────┐",
            "│    │    │    │",
            "│ P1 │ P2 │ P3 │",
            "│    │    │    │",
            "└────┴────┴────┘",
        ],
    ),
    LayoutTemplate(
        name="rows",
        description="Three equal rows",
        min_panes=3,
        ascii_preview=[
            "┌────────────┐",
            "│     P1     │",
            "├────────────┤",
            "│     P2     │",
            "├────────────┤",
            "│     P3     │",
            "└────────────┘",
        ],
    ),
    LayoutTemplate(
        name="tall",
        description="Main left + 2 rows right",
        min_panes=3,
        ascii_preview=[
            "┌────────┬─────┐",
            "│        │ P2  │",
            "│  Main  ├─────┤",
            "│        │ P3  │",
            "└────────┴─────┘",
        ],
    ),
    LayoutTemplate(
        name="wide",
        description="Main top + 2 cols bottom",
        min_panes=3,
        ascii_preview=[
            "┌────────────┐",
            "│    Main    │",
            "├──────┬─────┤",
            "│  P2  │ P3  │",
            "└──────┴─────┘",
        ],
    ),
    LayoutTemplate(
        name="fullscreen",
        description="Single pane fullscreen",
        min_panes=1,
        ascii_preview=[
            "┌────────────┐",
            "│            │",
            "│    Full    │",
            "│            │",
            "└────────────┘",
        ],
    ),
]


class PaneWorkspace:
    """Holds windows (each with a split tree) and one TerminalSession per leaf."""

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
        self.sessions: List[TerminalSession] = []
        self.windows: List[Window] = []
        self.current_window = 0
        self.web_mode: str = "normal"
        self.web_cmd_buffer: str = ""
        # zoom state (temporary view of a single pane)
        self.zoom_pane: int | None = None
        self._zoomed = False
        self._zoom_prev_tree: Tree | None = None
        self._zoom_prev_focus: int | None = None

        snap = restore
        if snap:
            tree = tree_from_json(snap.tree)
            n = count_panes(tree)
            shell = snap.shell if snap.shell is not None else cfg.shell
            for _ in range(n):
                self._append_session(24, 80, shell=shell, env=cfg.env)
            self.windows.append(Window(tree=tree, focus_pane=max(0, min(snap.focus_pane, n - 1))))
            if snap.buffer_dumps:
                for key, encoded in snap.buffer_dumps.items():
                    try:
                        idx = int(key)
                    except (ValueError, TypeError):
                        continue
                    if 0 <= idx < len(self.sessions):
                        self.sessions[idx].restore_buffer(encoded)
        else:
            self._append_session(24, 80, shell=cfg.shell, env=cfg.env)
            self.windows.append(Window(tree=0, focus_pane=0))

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

    def _append_session(
        self,
        rows: int,
        cols: int,
        *,
        shell: Optional[list[str]] = None,
        env: Optional[dict] = None,
    ) -> int:
        idx = len(self.sessions)
        self.sessions.append(
            TerminalSession(
                rows,
                cols,
                shell=shell if shell is not None else self.cfg.shell,
                env=env if env is not None else self.cfg.env,
                on_update=self._mark,
            )
        )
        return idx

    def split(self, direction: str) -> None:
        new_idx = self._append_session(
            24,
            80,
            shell=self.cfg.shell,
            env=self.cfg.env,
        )
        sub: Tree = (direction, 0.5, self.focus_pane, new_idx)
        self.tree = replace_pane(self.tree, self.focus_pane, sub)
        self.focus_pane = new_idx
        self._mark()
        emit_hook("pane_created", ExtensionContext(hook_name="pane_created", pane_index=new_idx))

    def resize_pane(self, direction: str) -> None:
        new_tree = adjust_ratio(self.tree, self.focus_pane, direction)
        if new_tree is not None:
            self.tree = new_tree
            self._mark()

    def only_pane(self) -> None:
        win = self._window()
        indices = pane_indices(win.tree)
        keep_idx = self.focus_pane
        keep = self.sessions[keep_idx]
        for idx in sorted(indices, reverse=True):
            if idx != keep_idx:
                emit_hook("pane_closed", ExtensionContext(hook_name="pane_closed", pane_index=idx))
                self.sessions[idx].close()
                del self.sessions[idx]
        for removed in sorted([i for i in indices if i != keep_idx], reverse=True):
            for w in self.windows:
                w.tree = reindex_after_remove(w.tree, removed)
                w.focus_pane = max(0, min(w.focus_pane, count_panes(w.tree) - 1))
        win.tree = 0
        win.focus_pane = 0
        self._mark()

    def remove_pane(self, idx: int) -> bool:
        if idx < 0 or idx >= len(self.sessions):
            return True

        emit_hook("pane_closed", ExtensionContext(hook_name="pane_closed", pane_index=idx))

        owner_window = None
        for wi, w in enumerate(self.windows):
            if idx in pane_indices(w.tree):
                owner_window = wi
                break

        if owner_window is None:
            if len(self.sessions) <= 1:
                self.sessions[idx].close()
                self.sessions = []
                self.tree = 0
                self.focus_pane = 0
                self._mark()
                return False
            self.sessions[idx].close()
            del self.sessions[idx]
            for w in self.windows:
                w.tree = reindex_after_remove(w.tree, idx)
                w.focus_pane = max(0, min(w.focus_pane, count_panes(w.tree) - 1))
            self._mark()
            return True

        if len(self.sessions) <= 1:
            self.sessions[idx].close()
            self.sessions = []
            self.tree = 0
            self.focus_pane = 0
            self._mark()
            return False

        self.sessions[idx].close()
        del self.sessions[idx]

        win = self.windows[owner_window]
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

        for i, w in enumerate(self.windows):
            if i != owner_window:
                w.tree = reindex_after_remove(w.tree, idx)
                w.focus_pane = max(0, min(w.focus_pane, count_panes(w.tree) - 1))

        self._mark()
        return True

    def focus_next(self) -> None:
        order = pane_indices(self.tree)
        if len(order) <= 1:
            return
        if self.focus_pane not in order:
            self.focus_pane = order[0]
            return
        pos = order.index(self.focus_pane)
        self.focus_pane = order[(pos + 1) % len(order)]
        self._mark()

    def focus_prev(self) -> None:
        order = pane_indices(self.tree)
        if len(order) <= 1:
            return
        if self.focus_pane not in order:
            self.focus_pane = order[0]
            return
        pos = order.index(self.focus_pane)
        self.focus_pane = order[(pos - 1) % len(order)]
        self._mark()

    def toggle_zoom(self) -> None:
        win = self._window()
        if not getattr(self, "_zoomed", False):
            # enter zoom: remember tree and focus, then set zoom_pane
            self._zoom_prev_tree = win.tree
            self._zoom_prev_focus = win.focus_pane
            self.zoom_pane = self.focus_pane
            self._zoomed = True
        else:
            # restore
            if self._zoom_prev_tree is not None:
                win.tree = self._zoom_prev_tree
            if self._zoom_prev_focus is not None:
                win.focus_pane = self._zoom_prev_focus
            self.zoom_pane = None
            self._zoomed = False
        self._mark()

    def sync_geometry(self, content_rows: int, content_cols: int) -> None:
        rects = assign_rects(
            self.tree,
            0,
            0,
            max(self.cfg.ui.min_pane_rows, content_rows),
            max(self.cfg.ui.min_pane_cols, content_cols),
        )

        for idx, r in rects.items():
            if 0 <= idx < len(self.sessions):
                self.sessions[idx].resize(
                    max(self.cfg.ui.min_pane_rows, r.rows - 2),
                    max(self.cfg.ui.min_pane_cols, r.cols - 2),
                )

    def active_session(self) -> TerminalSession:
        return self.sessions[self.focus_pane]

    def set_focus_pane(self, n: int) -> bool:
        if 0 <= n < len(self.sessions):
            old = self.focus_pane
            self.focus_pane = n
            self._mark()
            if old != n:
                emit_hook("pane_focus_changed", ExtensionContext(hook_name="pane_focus_changed", pane_index=n, message=str(old)))
            return True
        return False

    def pane_title(self, idx: int) -> str:
        s = self.sessions[idx]
        cwd = None
        if sys.platform != "win32" and os.name != "nt":
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
        for s in self.sessions:
            s.close()

    # ── window management ──────────────────────────────────────────

    def new_window(self) -> None:
        new_idx = self._append_session(24, 80, shell=self.cfg.shell, env=self.cfg.env)
        self.windows.append(Window(tree=new_idx, focus_pane=new_idx))
        self.current_window = len(self.windows) - 1
        self._mark()
        emit_hook("window_created", ExtensionContext(hook_name="window_created", window_index=self.current_window, pane_index=new_idx))

    def close_window(self) -> bool:
        if len(self.windows) <= 1:
            return False
        win_idx = self.current_window
        emit_hook("window_closed", ExtensionContext(hook_name="window_closed", window_index=win_idx))
        win = self.windows[win_idx]
        indices = sorted(pane_indices(win.tree), reverse=True)
        for idx in indices:
            if idx < len(self.sessions):
                self.sessions[idx].close()
                del self.sessions[idx]
        for removed in sorted(indices):
            for i, w in enumerate(self.windows):
                if i == self.current_window:
                    continue
                w.tree = reindex_after_remove(w.tree, removed)
        del self.windows[self.current_window]
        if self.current_window >= len(self.windows):
            self.current_window = len(self.windows) - 1
        self._mark()
        return True

    def next_window(self) -> None:
        if len(self.windows) <= 1:
            return
        self.current_window = (self.current_window + 1) % len(self.windows)
        self._mark()

    def prev_window(self) -> None:
        if len(self.windows) <= 1:
            return
        self.current_window = (self.current_window - 1) % len(self.windows)
        self._mark()

    def goto_window(self, n: int) -> bool:
        if 0 <= n < len(self.windows):
            self.current_window = n
            self._mark()
            return True
        return False

    # ── layout cycling ─────────────────────────────────────────────

    def cycle_layout(self) -> None:
        panes = pane_indices(self.tree)
        n = len(panes)
        if n <= 1:
            return

        current_name = self._detect_layout_name()
        try:
            idx = LAYOUT_CYCLE.index(current_name)
            next_name = LAYOUT_CYCLE[(idx + 1) % len(LAYOUT_CYCLE)]
        except ValueError:
            next_name = LAYOUT_CYCLE[0]

        new_tree = self._build_layout(panes, next_name)
        if new_tree is not None:
            self.tree = new_tree
            self._mark()

    def _detect_layout_name(self) -> str:
        panes = pane_indices(self.tree)
        n = len(panes)
        if n <= 1:
            return "even"
        if isinstance(self.tree, int):
            return "even"
        d, r, a, b = self.tree
        if d == "row" and abs(r - 0.5) < 0.05:
            return "even"
        if d == "row" and r > 0.5:
            return "main-vertical"
        if d == "col" and r > 0.5:
            return "main-horizontal"
        return "even"

    def _build_layout(self, panes: list[int], name: str) -> Tree | None:
        n = len(panes)
        if n <= 1:
            return panes[0] if panes else 0

        if name == "even":
            return self._build_even(panes)
        elif name == "main-vertical":
            return self._build_main_vertical(panes)
        elif name == "main-horizontal":
            return self._build_main_horizontal(panes)
        return None

    def _build_even(self, panes: list[int]) -> Tree:
        if len(panes) == 1:
            return panes[0]
        mid = len(panes) // 2
        left = self._build_even(panes[:mid])
        right = self._build_even(panes[mid:])
        return ("row", 0.5, left, right)

    def _build_main_vertical(self, panes: list[int]) -> Tree:
        if len(panes) == 1:
            return panes[0]
        main = panes[0]
        rest = panes[1:]
        if len(rest) == 1:
            return ("row", 0.6, main, rest[0])
        right_tree = self._build_even_vertical(rest)
        return ("row", 0.6, main, right_tree)

    def _build_main_horizontal(self, panes: list[int]) -> Tree:
        if len(panes) == 1:
            return panes[0]
        main = panes[0]
        rest = panes[1:]
        if len(rest) == 1:
            return ("col", 0.6, main, rest[0])
        bottom_tree = self._build_even_horizontal(rest)
        return ("col", 0.6, main, bottom_tree)

    def apply_layout_template(self, template_name: str) -> bool:
        tpl = None
        for t in LAYOUT_TEMPLATES:
            if t.name == template_name:
                tpl = t
                break
        if tpl is None:
            return False

        current_indices = pane_indices(self.tree)
        current_n = len(current_indices)
        needed = tpl.min_panes

        while current_n < needed:
            self._append_session(24, 80, shell=self.cfg.shell, env=self.cfg.env)
            current_n = len(self.sessions)

        all_indices = list(range(current_n))
        new_tree = self._build_template_tree(all_indices, template_name)
        if new_tree is None:
            return False

        used_indices = pane_indices(new_tree)
        unused = sorted([i for i in all_indices if i not in used_indices], reverse=True)
        for idx in unused:
            if idx < len(self.sessions):
                self.sessions[idx].close()
                emit_hook("pane_closed", ExtensionContext(hook_name="pane_closed", pane_index=idx))
        if unused:
            self.sessions = [s for i, s in enumerate(self.sessions) if i not in set(unused)]
            new_tree = _reindex_tree(new_tree, unused)

        for i in range(len(self.windows)):
            if i == self.current_window:
                self.windows[i].tree = new_tree
                self.windows[i].focus_pane = 0
            else:
                w_indices = pane_indices(self.windows[i].tree)
                target_n = len(used_indices)
                if len(w_indices) > target_n:
                    for removed in sorted([idx for idx in w_indices if idx >= target_n], reverse=True):
                        self.windows[i].tree = reindex_after_remove(self.windows[i].tree, removed)
                elif len(w_indices) < target_n:
                    self.windows[i].tree = self._build_template_tree(list(range(len(w_indices))), template_name) or self.windows[i].tree
                self.windows[i].focus_pane = max(0, min(self.windows[i].focus_pane, target_n - 1))

        self._mark()
        return True

    def _build_template_tree(self, panes: list[int], name: str) -> Tree | None:
        n = len(panes)
        if n == 0:
            return 0
        if n == 1:
            return panes[0]

        if name == "even-horizontal":
            return self._build_even_horizontal(panes)
        elif name == "even-vertical":
            return self._build_even_vertical(panes)
        elif name == "main-vertical":
            return self._build_main_vertical(panes)
        elif name == "main-horizontal":
            return self._build_main_horizontal(panes)
        elif name == "quad":
            return self._build_quad(panes)
        elif name == "columns":
            return self._build_columns(panes)
        elif name == "rows":
            return self._build_rows(panes)
        elif name == "tall":
            return self._build_tall(panes)
        elif name == "wide":
            return self._build_wide(panes)
        elif name == "fullscreen":
            return panes[0]
        return None

    def _build_even_horizontal(self, panes: list[int]) -> Tree:
        if len(panes) == 1:
            return panes[0]
        mid = len(panes) // 2
        left = self._build_even_horizontal(panes[:mid])
        right = self._build_even_horizontal(panes[mid:])
        return ("row", 0.5, left, right)

    def _build_even_vertical(self, panes: list[int]) -> Tree:
        if len(panes) == 1:
            return panes[0]
        mid = len(panes) // 2
        top = self._build_even_vertical(panes[:mid])
        bottom = self._build_even_vertical(panes[mid:])
        return ("col", 0.5, top, bottom)

    def _build_quad(self, panes: list[int]) -> Tree:
        if len(panes) < 4:
            return self._build_even_horizontal(panes)
        top_left = panes[0]
        top_right = panes[1]
        bot_left = panes[2]
        rest = panes[3:]
        if rest:
            bot_right = self._build_even_vertical(rest) if len(rest) > 1 else rest[0]
        else:
            bot_right = panes[3]
        top = ("row", 0.5, top_left, top_right)
        bot = ("row", 0.5, bot_left, bot_right)
        return ("col", 0.5, top, bot)

    def _build_columns(self, panes: list[int]) -> Tree:
        if len(panes) == 1:
            return panes[0]
        if len(panes) == 2:
            return ("row", 0.5, panes[0], panes[1])
        first = panes[0]
        rest = self._build_columns(panes[1:])
        ratio = 1.0 / len(panes)
        return ("row", ratio, first, rest)

    def _build_rows(self, panes: list[int]) -> Tree:
        if len(panes) == 1:
            return panes[0]
        if len(panes) == 2:
            return ("col", 0.5, panes[0], panes[1])
        first = panes[0]
        rest = self._build_rows(panes[1:])
        ratio = 1.0 / len(panes)
        return ("col", ratio, first, rest)

    def _build_tall(self, panes: list[int]) -> Tree:
        if len(panes) < 3:
            return self._build_main_vertical(panes)
        main = panes[0]
        top_right = panes[1]
        bottom_right = self._build_even_vertical(panes[2:]) if len(panes) > 3 else panes[2]
        right = ("col", 0.5, top_right, bottom_right)
        return ("row", 0.6, main, right)

    def _build_wide(self, panes: list[int]) -> Tree:
        if len(panes) < 3:
            return self._build_main_horizontal(panes)
        main = panes[0]
        bot_left = panes[1]
        bot_right = self._build_even_horizontal(panes[2:]) if len(panes) > 3 else panes[2]
        bottom = ("row", 0.5, bot_left, bot_right)
        return ("col", 0.6, main, bottom)


def try_load_snapshot(cfg: PlmuxConfig) -> SessionSnapshot | None:
    if not cfg.session.auto_save:
        return None
    return load_session(cfg)
"""File browser plugin for plmux.

Provides a :file-browser command that opens an interactive file browser overlay
with a tree view on the left and a file preview on the right.
"""

from __future__ import annotations

import os
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional

from rich import box
from rich.cells import cell_len
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from plmux.extensions import (
    plugin_metadata,
    register_command,
    register_overlay,
    register_mode_handler,
)
from plmux.input.commands import CommandResult

_MODE_NAME = "file_browser"
_OVERLAY_NAME = "file_browser"

plugin_metadata(
    name="file-browser",
    version="1.1.0",
    author="plmux",
    description="Interactive file browser overlay with tree view and file preview",
    config_schema={
        "show_hidden": {"type": "bool", "default": False, "description": "Show hidden files"},
        "preview_max_lines": {"type": "int", "default": 80, "description": "Max lines in file preview"},
    },
)

_BINARY_EXTENSIONS = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".svg",
    ".mp3", ".mp4", ".wav", ".avi", ".mkv", ".flac", ".ogg", ".wmv",
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar", ".zst",
    ".pyc", ".pyo", ".so", ".dll", ".dylib", ".o", ".a", ".lib",
    ".exe", ".bin", ".dat", ".db", ".sqlite", ".woff", ".woff2",
    ".eot", ".ttf", ".otf", ".pdf", ".doc", ".xls", ".ppt",
    ".class", ".jar", ".wasm", ".npy", ".npz", ".pkl",
})

_TEXT_EXTENSIONS = frozenset({
    ".txt", ".md", ".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".yaml",
    ".yml", ".toml", ".cfg", ".ini", ".conf", ".sh", ".bash", ".zsh",
    ".fish", ".rs", ".go", ".c", ".h", ".cpp", ".hpp", ".cs", ".java",
    ".rb", ".php", ".pl", ".lua", ".vim", ".el", ".clj", ".ex", ".exs",
    ".erl", ".hs", ".ml", ".scala", ".kt", ".swift", ".dart", ".r",
    ".sql", ".html", ".htm", ".css", ".scss", ".sass", ".less",
    ".xml", ".svg", ".log", ".csv", ".tsv", ".rst", ".tex", ".diff",
    ".patch", ".gitignore", ".dockerignore", ".env", ".makefile",
    ".cmake", ".gradle", ".properties", ".tf", ".proto", ".graphql",
    ".lock", ".mod", ".sum",
})

_PREVIEW_MAX_SIZE = 512 * 1024
_PREVIEW_MAX_LINES = 80
_DIR_CACHE_TTL = 2.0
_DIR_STAT_CACHE_TTL = 30.0
_PREVIEW_CACHE_SIZE = 64
_PREVIEW_DEBOUNCE_MS = 40
_SCROLL_DEBOUNCE_MS = 16

_DIR_MARKER_OPEN = "\u25BC"
_DIR_MARKER_CLOSED = "\u25B6"
_TREE_PIPE = "\u2502 "
_TREE_BRANCH = "\u251C\u2500"
_TREE_LAST = "\u2514\u2500"

_ICON_DIR = "\u25B8"
_ICON_DIR_OPEN = "\u25BE"
_ICON_FILE = " "
_ICON_LINK = "@"

_FILE_TYPE_TAGS: dict[str, tuple[str, str]] = {
    ".py": ("py", "#3572A5"),
    ".js": ("js", "#f1e05a"),
    ".ts": ("ts", "#3178c6"),
    ".tsx": ("tsx", "#3178c6"),
    ".jsx": ("jsx", "#61dafb"),
    ".rs": ("rs", "#dea584"),
    ".go": ("go", "#00add8"),
    ".java": ("java", "#b07219"),
    ".rb": ("rb", "#cc342d"),
    ".c": ("c", "#555555"),
    ".h": ("h", "#777"),
    ".cpp": ("c++", "#f34b7d"),
    ".hpp": ("h++", "#f34b7d"),
    ".cs": ("cs", "#178600"),
    ".md": ("md", "#519aba"),
    ".json": ("json", "#cbcb41"),
    ".yaml": ("yml", "#cb171e"),
    ".yml": ("yml", "#cb171e"),
    ".toml": ("toml", "#9c4221"),
    ".cfg": ("cfg", "#6a9955"),
    ".ini": ("ini", "#6a9955"),
    ".sh": ("sh", "#89e051"),
    ".bash": ("sh", "#89e051"),
    ".zsh": ("zsh", "#89e051"),
    ".html": ("html", "#e37933"),
    ".css": ("css", "#563d7c"),
    ".scss": ("scss", "#c6538c"),
    ".sql": ("sql", "#e38c00"),
    ".xml": ("xml", "#e37933"),
    ".env": ("env", "#ecd53f"),
    ".lock": ("lock", "#6a9955"),
    ".log": ("log", "#888"),
    ".txt": ("txt", "#888"),
    ".lua": ("lua", "#000080"),
    ".vim": ("vim", "#019833"),
    ".hs": ("hs", "#5e5086"),
    ".swift": ("swift", "#f05138"),
    ".kt": ("kt", "#a97bff"),
    ".dart": ("dart", "#00b4ab"),
    ".r": ("r", "#276dc3"),
    ".php": ("php", "#4f5d95"),
    ".pl": ("pl", "#0298c3"),
    ".ex": ("ex", "#6e4a7e"),
    ".erl": ("erl", "#b83998"),
    ".scala": ("scala", "#c22d40"),
    ".diff": ("diff", "#5c8a5c"),
    ".patch": ("patch", "#5c8a5c"),
    ".csv": ("csv", "#e38c00"),
    ".tf": ("tf", "#7b42bc"),
    ".proto": ("proto", "#3a7ca5"),
    ".graphql": ("gql", "#e535ab"),
}

_SPECIAL_FILE_TAGS: dict[str, tuple[str, str]] = {
    "makefile": ("make", "#6a9955"),
    "dockerfile": ("dock", "#6a9955"),
    "license": ("doc", "#519aba"),
    "readme": ("doc", "#519aba"),
}


@dataclass
class FileNode:
    name: str
    path: str
    is_dir: bool
    size: int = 0
    perms: str = ""
    mtime: float = 0.0
    expanded: bool = False
    loaded: bool = False
    children: List["FileNode"] = field(default_factory=list)
    tag: tuple[str, str] = ("", "")

    def __post_init__(self) -> None:
        if not self.is_dir and self.tag == ("", ""):
            self.tag = _compute_file_tag(self.name)


_dir_cache: dict[str, tuple[float, list[FileNode]]] = {}
_dir_stat_cache: dict[str, tuple[float, tuple[int, int, int]]] = {}
_preview_cache: OrderedDict[str, tuple[str, bool]] = OrderedDict()
_dir_stats_bg_results: dict[str, tuple[int, int, int]] = {}
_dir_stats_bg_lock = threading.Lock()


def _compute_file_tag(name: str) -> tuple[str, str]:
    suffix = Path(name).suffix.lower()
    tag = _FILE_TYPE_TAGS.get(suffix)
    if tag:
        return tag
    lower = name.lower()
    if lower.startswith(".git"):
        return ("git", "#f05032")
    special = _SPECIAL_FILE_TAGS.get(lower)
    if special:
        return special
    if lower.startswith("readme"):
        return ("doc", "#519aba")
    return ("", "")


def _format_size(size: int) -> str:
    if size < 1024:
        return f"{size}B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f}K"
    if size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f}M"
    return f"{size / (1024 * 1024 * 1024):.1f}G"


def _truncate_text(text: str, max_width: int, ellipsis: str = "...") -> str:
    if cell_len(text) <= max_width:
        return text
    ellipsis_len = cell_len(ellipsis)
    if max_width <= ellipsis_len:
        return text[:max_width]
    target = max_width - ellipsis_len
    result: list[str] = []
    result_len = 0
    for ch in text:
        ch_len = cell_len(ch)
        if result_len + ch_len > target:
            break
        result.append(ch)
        result_len += ch_len
    return "".join(result) + ellipsis


def _wrap_line(text: str, max_width: int) -> list[str]:
    if max_width <= 0:
        return [text] if text else []
    if not text:
        return [""]
    if cell_len(text) <= max_width:
        return [text]
    lines: list[str] = []
    current: list[str] = []
    current_len = 0
    for ch in text:
        ch_len = cell_len(ch)
        if current_len + ch_len > max_width and current:
            lines.append("".join(current))
            current = []
            current_len = 0
        current.append(ch)
        current_len += ch_len
    if current:
        lines.append("".join(current))
    return lines


def _format_perms(mode: int) -> str:
    p = ""
    for shift in (6, 3, 0):
        bits = (mode >> shift) & 7
        p += "r" if bits & 4 else "-"
        p += "w" if bits & 2 else "-"
        p += "x" if bits & 1 else "-"
    return p


def _compute_dir_stats_bg(path: str) -> None:
    total_dirs = 0
    total_files = 0
    total_size = 0
    try:
        for root, dirs, files in os.walk(path):
            total_dirs += len(dirs)
            for f in files:
                total_files += 1
                try:
                    total_size += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass
    except OSError:
        pass
    with _dir_stats_bg_lock:
        _dir_stats_bg_results[path] = (total_dirs, total_files, total_size)
        _dir_stat_cache[path] = (time.monotonic(), (total_dirs, total_files, total_size))


def _get_dir_stats(path: str) -> Optional[tuple[int, int, int]]:
    now = time.monotonic()
    cached = _dir_stat_cache.get(path)
    if cached is not None:
        ts, stats = cached
        if now - ts < _DIR_STAT_CACHE_TTL:
            return stats
    with _dir_stats_bg_lock:
        bg = _dir_stats_bg_results.get(path)
        if bg is not None:
            return bg
    threading.Thread(target=_compute_dir_stats_bg, args=(path,), daemon=True).start()
    return None


def _list_dir(path: str) -> list[FileNode]:
    now = time.monotonic()
    cached = _dir_cache.get(path)
    if cached is not None:
        ts, nodes = cached
        if now - ts < _DIR_CACHE_TTL:
            return nodes

    try:
        entries = sorted(os.scandir(path), key=lambda e: (not e.is_dir(), e.name.lower()))
    except (PermissionError, OSError):
        return []

    nodes: list[FileNode] = []
    for entry in entries:
        name = entry.name
        if name.startswith(".") and name not in (".env",):
            continue
        try:
            st = entry.stat()
            is_dir = entry.is_dir()
            node = FileNode(
                name=name,
                path=entry.path,
                is_dir=is_dir,
                size=st.st_size if not is_dir else 0,
                perms=_format_perms(st.st_mode),
                mtime=st.st_mtime,
            )
        except OSError:
            node = FileNode(
                name=name,
                path=entry.path,
                is_dir=entry.is_dir(),
            )
        nodes.append(node)

    _dir_cache[path] = (now, nodes)
    return nodes


def _ensure_children(node: FileNode) -> None:
    if node.is_dir and not node.loaded:
        node.children = _list_dir(node.path)
        node.loaded = True


def _flatten_tree_with_prefix(root_nodes: list[FileNode], expanded_set: set[str]) -> list[tuple[FileNode, str]]:
    result: list[tuple[FileNode, str]] = []

    def _walk(nodes: list[FileNode], prefix: str) -> None:
        last_idx = len(nodes) - 1
        for idx, node in enumerate(nodes):
            is_last = idx == last_idx
            if is_last:
                connector = _TREE_LAST + " "
            else:
                connector = _TREE_BRANCH + " "

            result.append((node, prefix + connector if prefix else ""))

            if node.is_dir and node.path in expanded_set:
                _ensure_children(node)
                if is_last:
                    child_prefix = prefix + "  "
                else:
                    child_prefix = prefix + _TREE_PIPE
                _walk(node.children, child_prefix)

    _walk(root_nodes, "")
    return result


def _is_text_file(path: str) -> bool:
    suffix = Path(path).suffix.lower()
    if suffix in _TEXT_EXTENSIONS:
        return True
    if suffix in _BINARY_EXTENSIONS:
        return False
    try:
        with open(path, "rb") as f:
            chunk = f.read(8192)
        return b"\x00" not in chunk
    except Exception:
        return False


def _read_preview(path: str) -> tuple[str, bool]:
    if path in _preview_cache:
        _preview_cache.move_to_end(path)
        return _preview_cache[path]

    try:
        st = os.stat(path)
        if st.st_size > _PREVIEW_MAX_SIZE:
            result = (f"[File too large: {_format_size(st.st_size)}]", False)
            _preview_cache[path] = result
            if len(_preview_cache) > _PREVIEW_CACHE_SIZE:
                _preview_cache.popitem(last=False)
            return result
    except OSError:
        result = ("[Cannot read file]", False)
        _preview_cache[path] = result
        if len(_preview_cache) > _PREVIEW_CACHE_SIZE:
            _preview_cache.popitem(last=False)
        return result

    if not _is_text_file(path):
        result = ("[Binary file]", False)
        _preview_cache[path] = result
        if len(_preview_cache) > _PREVIEW_CACHE_SIZE:
            _preview_cache.popitem(last=False)
        return result

    try:
        with open(path, "r", errors="replace") as f:
            lines: list[str] = []
            for i, line in enumerate(f):
                if i >= _PREVIEW_MAX_LINES:
                    lines.append("... (truncated)")
                    break
                lines.append(line.rstrip("\n\r"))
            result = ("\n".join(lines), True)
            _preview_cache[path] = result
            if len(_preview_cache) > _PREVIEW_CACHE_SIZE:
                _preview_cache.popitem(last=False)
            return result
    except Exception as exc:
        result = (f"[Error reading file: {exc}]", False)
        _preview_cache[path] = result
        if len(_preview_cache) > _PREVIEW_CACHE_SIZE:
            _preview_cache.popitem(last=False)
        return result


def _get_dir_info(path: str) -> str:
    try:
        st = os.stat(path)
        perms = _format_perms(st.st_mode)
        stats = _get_dir_stats(path)
        if stats is not None:
            r_dirs, r_files, r_size = stats
            return (
                f"{perms}\n\n"
                f"Directories:  {r_dirs}\n"
                f"Files:        {r_files}\n"
                f"Total size:   {_format_size(r_size)}"
            )
        return f"{perms}\n\nComputing directory stats..."
    except OSError:
        return ""


def _cmd_file_browser(ws: Any, args: list[str]) -> CommandResult:
    return CommandResult(plugin_overlay=_MODE_NAME)


def _on_enter(ctx: Any) -> None:
    root_path = os.getcwd()
    root_nodes = _list_dir(root_path)
    flat = _flatten_tree_with_prefix(root_nodes, set())
    ctx.plugin_state = {
        "root_path": root_path,
        "root_nodes": root_nodes,
        "expanded": frozenset(),
        "flat_cache": flat,
        "cursor": 0,
        "scroll_offset": 0,
        "preview_path": None,
        "preview_text": "",
        "preview_is_text": False,
        "_cached_expanded": frozenset(),
        "_last_preview_time": 0.0,
        "_pending_preview_node": None,
        "visible_rows": 20,
    }
    if flat:
        _update_preview(ctx.plugin_state, flat[0][0])


def _update_preview(state: dict, node: FileNode) -> None:
    if node.is_dir:
        info = _get_dir_info(node.path)
        state["preview_path"] = node.path
        state["preview_text"] = info
        state["preview_is_text"] = False
    else:
        text, is_text = _read_preview(node.path)
        state["preview_path"] = node.path
        state["preview_text"] = text
        state["preview_is_text"] = is_text


def _schedule_preview(state: dict, node: FileNode) -> None:
    now = time.monotonic()
    last = state.get("_last_preview_time", 0.0)
    elapsed_ms = (now - last) * 1000
    if elapsed_ms >= _PREVIEW_DEBOUNCE_MS:
        _update_preview(state, node)
        state["_last_preview_time"] = now
        state["_pending_preview_node"] = None
    else:
        state["_pending_preview_node"] = node


def _flush_pending_preview(state: dict) -> None:
    node = state.get("_pending_preview_node")
    if node is not None:
        _update_preview(state, node)
        state["_last_preview_time"] = time.monotonic()
        state["_pending_preview_node"] = None


def _get_flat(state: dict) -> list[tuple[FileNode, str]]:
    expanded = state.get("expanded", frozenset())
    cached_expanded = state.get("_cached_expanded")
    if cached_expanded is not None and cached_expanded == expanded:
        return state["flat_cache"]

    root_nodes = state.get("root_nodes", [])
    flat = _flatten_tree_with_prefix(root_nodes, set(expanded) if isinstance(expanded, frozenset) else expanded)
    state["flat_cache"] = flat
    state["_cached_expanded"] = expanded
    return flat


def _rebuild_flat(state: dict, expanded: set) -> list[tuple[FileNode, str]]:
    root_nodes = state.get("root_nodes", [])
    flat = _flatten_tree_with_prefix(root_nodes, expanded)
    state["flat_cache"] = flat
    state["_cached_expanded"] = frozenset(expanded)
    return flat


def handle_file_browser_mode(key: Any, ctx: Any) -> None:
    state = ctx.plugin_state
    if not state:
        ctx.mode = "normal"
        ctx.dirty = True
        return

    ch = str(key)
    name = key.name if hasattr(key, "name") else ""

    if name == "KEY_ESCAPE" or ch == "q":
        ctx.plugin_state = {}
        ctx.mode = "normal"
        ctx.dirty = True
        return

    expanded: set = set(state.get("expanded", frozenset()))
    cursor: int = state.get("cursor", 0)

    flat = _get_flat(state)
    if not flat:
        ctx.dirty = True
        return

    cursor = max(0, min(cursor, len(flat) - 1))
    current, _ = flat[cursor]
    need_rebuild = False

    if name in ("KEY_UP",) or ch == "k":
        cursor = max(0, cursor - 1)
    elif name in ("KEY_DOWN",) or ch == "j":
        cursor = min(len(flat) - 1, cursor + 1)
    elif name == "KEY_PGUP":
        half_page = max(1, state.get("visible_rows", 20) // 2)
        cursor = max(0, cursor - half_page)
    elif name == "KEY_PGDOWN":
        half_page = max(1, state.get("visible_rows", 20) // 2)
        cursor = min(len(flat) - 1, cursor + half_page)
    elif name == "KEY_HOME" or ch == "g":
        cursor = 0
    elif name == "KEY_END" or ch == "G":
        cursor = len(flat) - 1
    elif name == "KEY_ENTER" or ch in ("\n", "\r"):
        if current.is_dir:
            if current.path in expanded:
                expanded.discard(current.path)
                current.expanded = False
            else:
                expanded.add(current.path)
                current.expanded = True
                _ensure_children(current)
            need_rebuild = True
    elif ch == "l" and current.is_dir:
        if current.path not in expanded:
            expanded.add(current.path)
            current.expanded = True
            _ensure_children(current)
            need_rebuild = True
    elif ch == "h":
        if current.is_dir and current.path in expanded:
            expanded.discard(current.path)
            current.expanded = False
            need_rebuild = True
        else:
            parent_path = os.path.dirname(current.path)
            for i, (node, _) in enumerate(flat):
                if node.path == parent_path and node.is_dir and node.path in expanded:
                    expanded.discard(node.path)
                    node.expanded = False
                    need_rebuild = True
                    cursor = i
                    break
    elif ch == "r":
        _dir_cache.clear()
        _dir_stat_cache.clear()
        _preview_cache.clear()
        with _dir_stats_bg_lock:
            _dir_stats_bg_results.clear()
        root_path = state.get("root_path", os.getcwd())
        root_nodes = _list_dir(root_path)
        state["root_nodes"] = root_nodes
        need_rebuild = True

    if need_rebuild:
        flat = _rebuild_flat(state, expanded)
        cursor = max(0, min(cursor, len(flat) - 1))

    state["cursor"] = cursor
    state["expanded"] = frozenset(expanded)

    if 0 <= cursor < len(flat):
        _schedule_preview(state, flat[cursor][0])

    ctx.dirty = True


handle_file_browser_mode._on_enter = _on_enter


def _render_tree_row(
    node: FileNode,
    prefix: str,
    is_cursor: bool,
    tree_width: int,
    expanded_set: set[str],
) -> Text:
    row = Text()
    prefix_w = cell_len(prefix)
    tag, tag_color = node.tag

    if node.is_dir:
        icon = _ICON_DIR_OPEN if node.path in expanded_set else _ICON_DIR
        icon_w = cell_len(icon)
        used_w = prefix_w + icon_w + 2
        name_avail = tree_width - used_w
        display_name = _truncate_text(node.name, max(1, name_avail))

        row.append(prefix, style="dim #665c54")
        if is_cursor:
            row.append(f" {icon} ", style="bold #83a598 on #504945")
            row.append(display_name, style="bold #83a598 on #504945")
        else:
            row.append(f" {icon} ", style="#83a598")
            row.append(display_name, style="#83a598")
    elif tag:
        icon = tag
        icon_w = cell_len(icon)
        used_w = prefix_w + icon_w + 2
        name_avail = tree_width - used_w
        display_name = _truncate_text(node.name, max(1, name_avail))

        row.append(prefix, style="dim #665c54")
        if is_cursor:
            row.append(f" {icon} ", style=f"bold {tag_color} on #504945")
            row.append(display_name, style=f"bold {tag_color} on #504945")
        else:
            row.append(f" {icon} ", style=tag_color)
            row.append(display_name, style=tag_color)
    else:
        used_w = prefix_w + 3
        name_avail = tree_width - used_w
        display_name = _truncate_text(node.name, max(1, name_avail))

        row.append(prefix, style="dim #665c54")
        if is_cursor:
            row.append(f" {_ICON_FILE} ", style="on #504945")
            row.append(display_name, style="on #504945")
        else:
            row.append(f" {_ICON_FILE} ", style="")
            row.append(display_name, style="#d5c4a1")

    return row


def build_file_browser_overlay(
    theme: Any,
    *,
    terminal_width: int,
    terminal_height: int,
    plugin_state: dict,
) -> Panel:
    cursor: int = plugin_state.get("cursor", 0)
    scroll_offset: int = plugin_state.get("scroll_offset", 0)
    root_path: str = plugin_state.get("root_path", ".")
    preview_text: str = plugin_state.get("preview_text", "")
    preview_is_text: bool = plugin_state.get("preview_is_text", False)
    preview_path: str | None = plugin_state.get("preview_path")
    expanded_set: set = set(plugin_state.get("expanded", frozenset()))

    _flush_pending_preview(plugin_state)
    preview_text = plugin_state.get("preview_text", "")
    preview_is_text = plugin_state.get("preview_is_text", False)
    preview_path = plugin_state.get("preview_path")

    flat = _get_flat(plugin_state)
    total = len(flat)
    cursor = max(0, min(cursor, total - 1)) if flat else 0

    max_w = min(terminal_width - 4, 100)
    max_h = min(terminal_height - 4, 40)

    tree_width = max(28, max_w // 3)
    preview_width = max_w - tree_width - 4

    visible_rows = max(1, max_h - 6)
    _SCROLL_MARGIN = max(2, visible_rows // 6)

    if total <= visible_rows:
        scroll_offset = 0
    else:
        if cursor < scroll_offset + _SCROLL_MARGIN:
            scroll_offset = cursor - _SCROLL_MARGIN
        elif cursor >= scroll_offset + visible_rows - _SCROLL_MARGIN:
            scroll_offset = cursor - visible_rows + _SCROLL_MARGIN + 1
        scroll_offset = max(0, min(scroll_offset, total - visible_rows))

    plugin_state["scroll_offset"] = scroll_offset
    plugin_state["visible_rows"] = visible_rows

    visible_end = min(scroll_offset + visible_rows, total)

    tree_grid = Table.grid(padding=(0, 0))
    tree_grid.add_column(width=tree_width)

    header = Text()
    header.append(" /", style="bold #fabd2f")
    header.append(root_path, style="bold white")
    tree_grid.add_row(header)
    tree_grid.add_row(Text(""))

    if scroll_offset > 0:
        tree_grid.add_row(Text(f"  \u2502 \u2191{scroll_offset}", style="dim #665c54"))

    for i in range(scroll_offset, visible_end):
        node, prefix = flat[i]
        row = _render_tree_row(node, prefix, i == cursor, tree_width, expanded_set)
        tree_grid.add_row(row)

    if visible_end < total:
        remaining = total - visible_end
        tree_grid.add_row(Text(f"  \u2502 \u2193{remaining}", style="dim #665c54"))

    preview_grid = Table.grid(padding=(0, 0))
    preview_grid.add_column(width=preview_width)

    if preview_path:
        node_name = os.path.basename(preview_path)
        preview_header = Text()
        preview_header.append(" Preview ", style="bold underline")
        header_avail = preview_width - 10
        display_node_name = _truncate_text(node_name, max(1, header_avail))
        preview_header.append(display_node_name, style="bold yellow")
        preview_grid.add_row(preview_header)

        if preview_is_text:
            content_width = preview_width - 6
            text_grid = Table.grid(padding=(0, 0))
            text_grid.add_column(width=4)
            text_grid.add_column(width=1)
            text_grid.add_column()
            for line_no, line in enumerate(preview_text.split("\n"), 1):
                wrapped = _wrap_line(line, max(1, content_width))
                for wi, segment in enumerate(wrapped):
                    if wi == 0:
                        text_grid.add_row(
                            Text(f"{line_no:>4}", style="dim #5c6370"),
                            Text(" "),
                            Text(segment, style="white"),
                        )
                    else:
                        text_grid.add_row(
                            Text("    ", style="dim #5c6370"),
                            Text(" "),
                            Text(segment, style="white"),
                        )
            preview_grid.add_row(text_grid)
        else:
            content_width = preview_width - 2
            continuation_indent = "  "
            for line in preview_text.split("\n"):
                wrapped = _wrap_line(line, max(1, content_width))
                for wi, segment in enumerate(wrapped):
                    if wi == 0:
                        preview_grid.add_row(Text(segment, style="dim italic"))
                    else:
                        preview_grid.add_row(Text(continuation_indent + segment, style="dim italic"))
    else:
        preview_grid.add_row(Text("Select a file to preview", style="dim italic"))

    body = Table.grid(padding=(0, 2))
    body.add_column()
    body.add_column()
    body.add_row(tree_grid, preview_grid)

    footer = Text()
    footer.append(" j/k ", style="bold black on #85c751")
    footer.append(" nav  ", style="dim")
    footer.append(" Enter ", style="bold black on #85c751")
    footer.append(" toggle  ", style="dim")
    footer.append(" h/l ", style="bold black on #85c751")
    footer.append(" fold  ", style="dim")
    footer.append(" r ", style="bold black on #85c751")
    footer.append(" refresh  ", style="dim")
    footer.append(" Esc ", style="bold black on #85c751")
    footer.append(" close", style="dim")

    inner = Table.grid(padding=(0, 1))
    inner.add_row(body)
    inner.add_row("")
    inner.add_row(footer)

    return Panel(
        inner,
        title=" FILE BROWSER ",
        title_align="left",
        border_style=theme.pane_active_border if hasattr(theme, "pane_active_border") else "blue",
        box=box.HEAVY,
        width=max_w,
        height=max_h,
        padding=(1, 2),
    )


register_command("file-browser", _cmd_file_browser)
register_command("fb", _cmd_file_browser)
register_overlay(_OVERLAY_NAME, build_file_browser_overlay)
register_mode_handler(_MODE_NAME, handle_file_browser_mode)

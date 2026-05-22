"""File browser plugin for plmux.

Provides a :file-browser command that opens an interactive file browser overlay
with a tree view on the left and a file preview on the right.
"""

from __future__ import annotations

import os
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List

from rich import box
from rich.cells import cell_len
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from plmux.extensions import (
    register_command,
    register_overlay,
    register_mode_handler,
)
from plmux.input.commands import CommandResult

_MODE_NAME = "file_browser"
_OVERLAY_NAME = "file_browser"

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

_DIR_MARKER_OPEN = "\u25BC"
_DIR_MARKER_CLOSED = "\u25B6"
_TREE_PIPE = "\u2502 "
_TREE_BRANCH = "\u251C\u2500"
_TREE_LAST = "\u2514\u2500"


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


_dir_cache: dict[str, tuple[float, list[FileNode]]] = {}
_dir_stat_cache: dict[str, tuple[float, tuple[int, int, int]]] = {}
_preview_cache: OrderedDict[str, tuple[str, bool]] = OrderedDict()


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
    result = []
    result_len = 0
    for ch in text:
        ch_len = cell_len(ch)
        if result_len + ch_len > target:
            break
        result.append(ch)
        result_len += ch_len
    return "".join(result) + ellipsis


def _format_perms(mode: int) -> str:
    p = ""
    for shift in (6, 3, 0):
        bits = (mode >> shift) & 7
        p += "r" if bits & 4 else "-"
        p += "w" if bits & 2 else "-"
        p += "x" if bits & 1 else "-"
    return p


def _compute_dir_stats(path: str) -> tuple[int, int, int]:
    now = time.monotonic()
    cached = _dir_stat_cache.get(path)
    if cached is not None:
        ts, stats = cached
        if now - ts < _DIR_STAT_CACHE_TTL:
            return stats

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

    result = (total_dirs, total_files, total_size)
    _dir_stat_cache[path] = (now, result)
    return result


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

    nodes = []
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
            lines = []
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
        r_dirs, r_files, r_size = _compute_dir_stats(path)
        return (
            f"{perms}\n\n"
            f"Directories:  {r_dirs}\n"
            f"Files:        {r_files}\n"
            f"Total size:   {_format_size(r_size)}"
        )
    except OSError:
        return ""


def _cmd_file_browser(ws, args: list[str]) -> CommandResult:
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
    }
    if flat:
        _update_preview(ctx, flat[0][0])


def _update_preview(ctx: Any, node: FileNode) -> None:
    state = ctx.plugin_state
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


def handle_file_browser_mode(key, ctx: Any) -> None:
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

    if name in ("KEY_UP",) or ch == "k":
        cursor = max(0, cursor - 1)
    elif name in ("KEY_DOWN",) or ch == "j":
        cursor = min(len(flat) - 1, cursor + 1)
    elif name == "KEY_PGUP":
        cursor = max(0, cursor - 10)
    elif name == "KEY_PGDOWN":
        cursor = min(len(flat) - 1, cursor + 10)
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
            flat = _flatten_tree_with_prefix(state.get("root_nodes", []), expanded)
            state["flat_cache"] = flat
            state["_cached_expanded"] = frozenset(expanded)
            cursor = max(0, min(cursor, len(flat) - 1))
    elif ch == "l" and current.is_dir:
        if current.path not in expanded:
            expanded.add(current.path)
            current.expanded = True
            _ensure_children(current)
            flat = _flatten_tree_with_prefix(state.get("root_nodes", []), expanded)
            state["flat_cache"] = flat
            state["_cached_expanded"] = frozenset(expanded)
    elif ch == "h":
        if current.is_dir and current.path in expanded:
            expanded.discard(current.path)
            current.expanded = False
            flat = _flatten_tree_with_prefix(state.get("root_nodes", []), expanded)
            state["flat_cache"] = flat
            state["_cached_expanded"] = frozenset(expanded)
            cursor = max(0, min(cursor, len(flat) - 1))
        else:
            parent_path = os.path.dirname(current.path)
            for i, (node, _) in enumerate(flat):
                if node.path == parent_path and node.is_dir and node.path in expanded:
                    expanded.discard(node.path)
                    node.expanded = False
                    flat = _flatten_tree_with_prefix(state.get("root_nodes", []), expanded)
                    state["flat_cache"] = flat
                    state["_cached_expanded"] = frozenset(expanded)
                    cursor = i
                    break
    elif ch == "r":
        _dir_cache.clear()
        _dir_stat_cache.clear()
        _preview_cache.clear()
        root_path = state.get("root_path", os.getcwd())
        root_nodes = _list_dir(root_path)
        state["root_nodes"] = root_nodes
        flat = _flatten_tree_with_prefix(root_nodes, expanded)
        state["flat_cache"] = flat
        state["_cached_expanded"] = frozenset(expanded)
        cursor = max(0, min(cursor, len(flat) - 1))

    state["cursor"] = cursor
    state["expanded"] = frozenset(expanded)

    if 0 <= cursor < len(flat):
        _update_preview(ctx, flat[cursor][0])

    ctx.dirty = True


handle_file_browser_mode._on_enter = _on_enter


def _file_type_tag(name: str) -> tuple[str, str]:
    suffix = Path(name).suffix.lower()
    tags = {
        ".py": ("py", "bold white on #306998"),
        ".js": ("js", "bold white on #f7df1e"),
        ".ts": ("ts", "bold white on #3178c6"),
        ".tsx": ("tsx", "bold white on #3178c6"),
        ".jsx": ("jsx", "bold white on #61dafb"),
        ".rs": ("rs", "bold white on #dea584"),
        ".go": ("go", "bold white on #00add8"),
        ".java": ("java", "bold white on #b07219"),
        ".rb": ("rb", "bold white on #cc342d"),
        ".c": ("c", "bold white on #555555"),
        ".h": ("h", "bold white on #555555"),
        ".cpp": ("c++", "bold white on #f34b7d"),
        ".hpp": ("h++", "bold white on #f34b7d"),
        ".cs": ("cs", "bold white on #178600"),
        ".md": ("md", "bold white on #083fa1"),
        ".json": ("json", "bold black on #f1e05a"),
        ".yaml": ("yml", "bold white on #cb171e"),
        ".yml": ("yml", "bold white on #cb171e"),
        ".toml": ("toml", "bold white on #9c4221"),
        ".cfg": ("cfg", "bold white on #555"),
        ".ini": ("ini", "bold white on #555"),
        ".sh": ("sh", "bold white on #89e051"),
        ".bash": ("sh", "bold white on #89e051"),
        ".zsh": ("zsh", "bold white on #89e051"),
        ".html": ("html", "bold white on #e34c26"),
        ".css": ("css", "bold white on #563d7c"),
        ".scss": ("scss", "bold white on #c6538c"),
        ".sql": ("sql", "bold white on #e38c00"),
        ".xml": ("xml", "bold white on #555"),
        ".env": ("env", "bold white on #ecd53f"),
        ".lock": ("lock", "bold white on #555"),
        ".log": ("log", "bold white on #555"),
        ".txt": ("txt", "bold white on #555"),
        ".lua": ("lua", "bold white on #000080"),
        ".vim": ("vim", "bold white on #019833"),
        ".hs": ("hs", "bold white on #5e5086"),
        ".swift": ("swift", "bold white on #f05138"),
        ".kt": ("kt", "bold white on #a97bff"),
        ".dart": ("dart", "bold white on #00b4ab"),
        ".r": ("r", "bold white on #276dc3"),
        ".php": ("php", "bold white on #4f5d95"),
        ".pl": ("pl", "bold white on #0298c3"),
        ".ex": ("ex", "bold white on #6e4a7e"),
        ".erl": ("erl", "bold white on #b83998"),
        ".scala": ("scala", "bold white on #c22d40"),
        ".diff": ("diff", "bold white on #3a3"),
        ".patch": ("patch", "bold white on #3a3"),
        ".csv": ("csv", "bold white on #e38c00"),
        ".tf": ("tf", "bold white on #7b42bc"),
        ".proto": ("proto", "bold white on #3a7ca5"),
        ".graphql": ("gql", "bold white on #e535ab"),
    }
    tag, style = tags.get(suffix, ("", ""))
    if not tag:
        if name == "Makefile" or name == "Dockerfile":
            return (name[:4].lower(), "bold white on #555")
        if name == "LICENSE" or name == "README" or name.startswith("README"):
            return ("doc", "bold white on #083fa1")
        if name.startswith(".git"):
            return ("git", "bold white on #f05032")
        return ("", "")
    return (tag, style)


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

    flat = _get_flat(plugin_state)
    total = len(flat)
    cursor = max(0, min(cursor, total - 1)) if flat else 0

    max_w = min(terminal_width - 4, 100)
    max_h = min(terminal_height - 4, 40)

    tree_width = max(28, max_w // 3)
    preview_width = max_w - tree_width - 4

    visible_rows = max(1, max_h - 6)

    if total <= visible_rows:
        scroll_offset = 0
    else:
        if cursor < scroll_offset:
            scroll_offset = cursor
        elif cursor >= scroll_offset + visible_rows:
            scroll_offset = cursor - visible_rows + 1
        scroll_offset = max(0, min(scroll_offset, total - visible_rows))

    plugin_state["scroll_offset"] = scroll_offset

    visible_end = min(scroll_offset + visible_rows, total)

    tree_grid = Table.grid(padding=(0, 0))
    tree_grid.add_column(width=tree_width)

    header = Text()
    header.append(" /", style="bold #fabd2f")
    header.append(root_path, style="bold white")
    tree_grid.add_row(header)
    tree_grid.add_row(Text(""))

    if scroll_offset > 0:
        tree_grid.add_row(Text(f"  \u2502 ({scroll_offset} above)", style="dim cyan"))

    for i in range(scroll_offset, visible_end):
        node, prefix = flat[i]
        row = Text()

        cursor_indicator = " \u25B6" if i == cursor else "  "
        cursor_w = cell_len(cursor_indicator)
        prefix_w = cell_len(prefix)
        tag_w = 0
        tag, tag_style = _file_type_tag(node.name)

        if node.is_dir:
            marker = f" {_DIR_MARKER_OPEN} " if node.path in expanded_set else f" {_DIR_MARKER_CLOSED} "
            marker_w = cell_len(marker)
            used_w = cursor_w + prefix_w + marker_w + 1
            name_avail = tree_width - used_w
            display_name = _truncate_text(node.name, max(1, name_avail - 1))

            if i == cursor:
                row.append(cursor_indicator, style="bold black on #85c751")
            else:
                row.append(cursor_indicator)
            row.append(prefix, style="dim #5c6370")
            row.append(marker, style="bold cyan")
            if i == cursor:
                row.append(display_name, style="bold black on #85c751")
            else:
                row.append(display_name, style="bold cyan")
            row.append("/", style="cyan")
        else:
            if tag:
                tag_str = f" {tag} "
                tag_w = cell_len(tag_str)
                row.append(cursor_indicator, style="bold black on #85c751" if i == cursor else "")
                row.append(prefix, style="dim #5c6370")
                row.append(tag_str, style=tag_style)
                row.append(" ", style="")
            else:
                tag_w = 3
                row.append(cursor_indicator, style="bold black on #85c751" if i == cursor else "")
                row.append(prefix, style="dim #5c6370")
                row.append("   ")

            used_w = cursor_w + prefix_w + tag_w
            name_avail = tree_width - used_w
            display_name = _truncate_text(node.name, max(1, name_avail))

            if i == cursor:
                row.append(display_name, style="bold black on #85c751")
            else:
                row.append(display_name, style="white")

        tree_grid.add_row(row)

    if visible_end < total:
        remaining = total - visible_end
        tree_grid.add_row(Text(f"  \u2502 ({remaining} below)", style="dim cyan"))

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
            for line_no, line in enumerate(preview_text.split("\n"), 1):
                display_line = _truncate_text(line, max(1, content_width))
                num = Text(f"{line_no:4} ", style="dim #5c6370")
                content = Text(display_line, style="white")
                preview_grid.add_row(Text.assemble(num, content))
        else:
            content_width = preview_width - 2
            for line in preview_text.split("\n"):
                display_line = _truncate_text(line, max(1, content_width))
                preview_grid.add_row(Text(display_line, style="dim italic"))
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

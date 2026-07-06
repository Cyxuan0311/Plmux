"""Shared command definitions and dispatchers for REST API and MCP server.

Provides a common action-based API that maps named actions with typed
arguments to TmuxServer operations and IPC COMMAND messages.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


ACTION_REGISTRY: Dict[str, Dict[str, Any]] = {}


def register_action(
    name: str,
    description: str,
    params: Optional[List[Dict[str, Any]]] = None,
    category: str = "general",
) -> None:
    ACTION_REGISTRY[name] = {
        "name": name,
        "description": description,
        "params": params or [],
        "category": category,
    }


def action_list() -> List[Dict[str, Any]]:
    return [
        {"name": a["name"], "description": a["description"], "params": a["params"], "category": a["category"]}
        for a in ACTION_REGISTRY.values()
    ]


def action_list_grouped() -> Dict[str, List[Dict[str, Any]]]:
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for a in ACTION_REGISTRY.values():
        cat = a["category"]
        if cat not in groups:
            groups[cat] = []
        groups[cat].append(a)
    return groups


# ── Sessions ─────────────────────────────────────────────────────────────────

register_action("list_sessions", "List all active sessions", category="sessions")
register_action("create_session", "Create a new detached session", params=[
    {"name": "session_name", "type": "string", "required": False, "description": "Optional session name"},
], category="sessions")
register_action("kill_session", "Kill a session by index or name", params=[
    {"name": "session", "type": "string|int", "required": True, "description": "Session index or name"},
], category="sessions")
register_action("switch_session", "Switch to a session by index", params=[
    {"name": "index", "type": "int", "required": True, "description": "Session index"},
], category="sessions")
register_action("rename_session", "Rename the current session", params=[
    {"name": "name", "type": "string", "required": True, "description": "New session name"},
], category="sessions")

# ── Windows ──────────────────────────────────────────────────────────────────

register_action("new_window", "Create a new window", category="windows")
register_action("close_window", "Close the current window", category="windows")
register_action("next_window", "Switch to the next window", category="windows")
register_action("prev_window", "Switch to the previous window", category="windows")
register_action("goto_window", "Go to a specific window by index", params=[
    {"name": "index", "type": "int", "required": True, "description": "Window index (0-based)"},
], category="windows")
register_action("rename_window", "Rename the current window", params=[
    {"name": "name", "type": "string", "required": True, "description": "New window name"},
], category="windows")

# ── Panes ────────────────────────────────────────────────────────────────────

register_action("split_horizontal", "Split the current pane horizontally (stacked)", category="panes")
register_action("split_vertical", "Split the current pane vertically (side-by-side)", category="panes")
register_action("focus_pane", "Focus a specific pane by index", params=[
    {"name": "index", "type": "int", "required": True, "description": "Pane index (0-based)"},
], category="panes")
register_action("focus_direction", "Focus a pane in a direction", params=[
    {"name": "direction", "type": "string", "required": True, "description": "left|right|up|down"},
], category="panes")
register_action("kill_pane", "Kill a pane by index", params=[
    {"name": "index", "type": "int", "required": False, "description": "Pane index (default: focused)"},
], category="panes")
register_action("swap_pane", "Swap pane position", params=[
    {"name": "direction", "type": "string", "required": True, "description": "up|down"},
], category="panes")
register_action("break_pane", "Move the current pane to a new window", category="panes")
register_action("join_pane", "Join a pane from another window", params=[
    {"name": "direction", "type": "string", "required": False, "description": "horizontal|vertical (default: horizontal)"},
], category="panes")
register_action("respawn_pane", "Respawn a pane", params=[
    {"name": "index", "type": "int", "required": False, "description": "Pane index (default: focused)"},
], category="panes")
register_action("resize_pane", "Resize a pane in a direction", params=[
    {"name": "direction", "type": "string", "required": True, "description": "left|right|up|down"},
], category="panes")
register_action("toggle_zoom", "Toggle zoom on the current pane", category="panes")
register_action("only_pane", "Keep only the current pane (close all others)", category="panes")
register_action("cycle_layout", "Cycle through pane layouts", category="panes")
register_action("rotate_panes", "Rotate pane positions", params=[
    {"name": "direction", "type": "string", "required": False, "description": "up|down (default: up)"},
], category="panes")
register_action("apply_layout", "Apply a named layout template", params=[
    {"name": "name", "type": "string", "required": True, "description": "Layout template name"},
], category="panes")

# ── Input ────────────────────────────────────────────────────────────────────

register_action("send_keys", "Send text to the current pane", params=[
    {"name": "text", "type": "string", "required": True, "description": "Text to send"},
], category="input")

# ── Buffers ──────────────────────────────────────────────────────────────────

register_action("list_buffers", "List all paste buffers", category="buffers")
register_action("set_buffer", "Set a paste buffer", params=[
    {"name": "data", "type": "string", "required": True, "description": "Buffer content"},
], category="buffers")
register_action("show_buffer", "Show buffer contents", params=[
    {"name": "name", "type": "string", "required": False, "description": "Buffer name (default: first)"},
], category="buffers")
register_action("paste_buffer", "Paste buffer contents into the current pane", params=[
    {"name": "name", "type": "string", "required": False, "description": "Buffer name (default: first)"},
], category="buffers")
register_action("delete_buffer", "Delete a paste buffer", params=[
    {"name": "name", "type": "string", "required": True, "description": "Buffer name"},
], category="buffers")
register_action("save_buffer", "Save a buffer to a file", params=[
    {"name": "name", "type": "string", "required": True, "description": "Buffer name"},
    {"name": "path", "type": "string", "required": True, "description": "File path"},
], category="buffers")
register_action("load_buffer", "Load a buffer from a file", params=[
    {"name": "path", "type": "string", "required": True, "description": "File path"},
    {"name": "buffer_name", "type": "string", "required": False, "description": "Buffer name (optional)"},
], category="buffers")

# ── Environment ──────────────────────────────────────────────────────────────

register_action("get_environment", "Show session environment variables", category="environment")
register_action("set_environment", "Set a session environment variable", params=[
    {"name": "key", "type": "string", "required": True, "description": "Variable name"},
    {"name": "value", "type": "string", "required": True, "description": "Variable value"},
], category="environment")
register_action("unset_environment", "Unset a session environment variable", params=[
    {"name": "key", "type": "string", "required": True, "description": "Variable name"},
], category="environment")

# ── Config / Options ─────────────────────────────────────────────────────────

register_action("set_option", "Set a runtime option", params=[
    {"name": "name", "type": "string", "required": True, "description": "Option name"},
    {"name": "value", "type": "string", "required": True, "description": "Option value"},
], category="config")
register_action("show_options", "Show all runtime options", category="config")
register_action("reload_config", "Reload configuration and plugins", category="config")
register_action("bind_key", "Bind a key to an action", params=[
    {"name": "key", "type": "string", "required": True, "description": "Key name"},
    {"name": "action", "type": "string", "required": True, "description": "Action name"},
], category="config")
register_action("unbind_key", "Unbind a key", params=[
    {"name": "key", "type": "string", "required": True, "description": "Key name"},
], category="config")

# ── Theme ────────────────────────────────────────────────────────────────────

register_action("list_themes", "List available themes", category="theme")
register_action("set_theme", "Set the active theme", params=[
    {"name": "name", "type": "string", "required": True, "description": "Theme name"},
], category="theme")

# ── Web ──────────────────────────────────────────────────────────────────────

register_action("start_web", "Start the web client on a port", params=[
    {"name": "port", "type": "int", "required": False, "description": "Port number (default: 9888)"},
], category="web")
register_action("stop_web", "Stop the web client", category="web")

# ── General ──────────────────────────────────────────────────────────────────

register_action("display_panes", "Show pane numbers temporarily", category="general")
register_action("server_status", "Get daemon server status", category="general")
register_action("help", "Show help information", category="general")

# ── Daemon raw command dispatch ──────────────────────────────────────────────


async def handle_command_from_dict(
    send_cmd, ws_ref, action: str, params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Dispatch a named action to either an IPC command or a direct ws call.

    Args:
        send_cmd: Async callable that sends a command dict to the daemon.
        ws_ref: The TmuxServer workspace reference (may be None in REST mode).
        action: The action name.
        params: Optional dict of action parameters.

    Returns:
        A dict with keys: success (bool), message (str), data (any).
    """
    params = params or {}
    cmd_map = _build_ipc_command(action, params)
    if cmd_map:
        try:
            await send_cmd(cmd_map)
            return {"success": True, "message": f"Action '{action}' executed", "data": cmd_map}
        except Exception as e:
            return {"success": False, "message": f"Action '{action}' failed: {e}", "data": None}
    return {"success": False, "message": f"Unknown action: {action}", "data": None}


def _build_ipc_command(action: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Build an IPC command dict from a named action + params.

    Returns None if the action is unknown or not available via IPC COMMAND.
    """
    mapping = {
        "split_horizontal": lambda p: {"action": "split", "direction": "col"},
        "split_vertical": lambda p: {"action": "split", "direction": "row"},
        "only_pane": lambda p: {"action": "only_pane"},
        "new_window": lambda p: {"action": "new_window"},
        "close_window": lambda p: {"action": "close_window"},
        "next_window": lambda p: {"action": "next_window"},
        "prev_window": lambda p: {"action": "prev_window"},
        "goto_window": lambda p: {"action": "goto_window", "index": int(p.get("index", 0))},
        "focus_pane": lambda p: {"action": "set_focus_pane", "index": int(p.get("index", 0))},
        "focus_direction": lambda p: {"action": "focus_direction", "direction": str(p.get("direction", "left"))},
        "kill_pane": lambda p: {"action": "kill_pane", "pane_index": int(p.get("index", 0)) if "index" in p else None},
        "swap_pane": lambda p: {"action": "swap_pane", "direction": str(p.get("direction", "up"))},
        "break_pane": lambda p: {"action": "break_pane"},
        "join_pane": lambda p: {"action": "join_pane", "direction": str(p.get("direction", "row"))},
        "respawn_pane": lambda p: {"action": "respawn_pane", "pane_index": int(p.get("index", 0)) if "index" in p else None},
        "resize_pane": lambda p: {"action": "resize_pane", "direction": str(p.get("direction", "left"))},
        "toggle_zoom": lambda p: {"action": "toggle_zoom"},
        "rotate_panes": lambda p: {"action": "rotate_panes", "direction": str(p.get("direction", "up"))},
        "cycle_layout": lambda p: {"action": "cycle_layout"},
        "send_keys": lambda p: {"action": "send_keys", "text": str(p.get("text", ""))},
        "rename_window": lambda p: {"action": "rename_window", "name": str(p.get("name", ""))},
        "rename_session": lambda p: {"action": "rename_session", "name": str(p.get("name", ""))},
        "new_session": lambda p: {"action": "new_session", "name": str(p.get("session_name", ""))},
        "switch_session": lambda p: {"action": "switch_session", "index": int(p.get("index", 0))},
        "kill_session": lambda p: {"action": "kill_session", "index": int(p.get("index", 0)) if "index" in p else None},
        "next_session": lambda p: {"action": "next_session"},
        "prev_session": lambda p: {"action": "prev_session"},
        "apply_layout": lambda p: {"action": "apply_layout_template", "name": str(p.get("name", ""))},
        "display_panes": lambda p: {"action": "display_panes"},
    }
    builder = mapping.get(action)
    if builder is None:
        return None
    cmd = builder(params)
    cmd = {k: v for k, v in cmd.items() if v is not None}
    return cmd

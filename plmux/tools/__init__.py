"""Tools module: REST API and MCP server for AI integration.

This module provides:
- REST API: through the plmux web server (port 9888 by default)
- MCP server: a Model Context Protocol server for AI assistants

It depends on the WebSocket server infrastructure already in plmux.
"""

from __future__ import annotations

from plmux.tools.rest_commands import action_list, handle_command_from_dict

__all__ = [
    "action_list",
    "handle_command_from_dict",
]

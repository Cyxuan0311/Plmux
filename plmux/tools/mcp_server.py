"""MCP (Model Context Protocol) server for plmux AI integration.

Allows AI assistants (Claude Desktop, Cursor, VS Code, etc.) to discover
and call all plmux operations as tools via the standard Model Context
Protocol (JSON-RPC over stdio).

Usage:
    plmux --mcp
    # or:
    python -m plmux.tools.mcp_server

For Claude Desktop integration, add to your claude_desktop_config.json:
    {
        "mcpServers": {
            "plmux": {
                "command": "plmux",
                "args": ["--mcp"]
            }
        }
    }
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any, Dict, List, Optional

from plmux.daemon.client import attach_to_server, is_server_alive
from plmux.tools.rest_commands import action_list, handle_command_from_dict


MCP_PROTOCOL_VERSION = "2024-11-05"


def _mcp_tools() -> List[Dict[str, Any]]:
    """Build the list of MCP tool definitions from the action registry."""
    tools = []
    for action in action_list():
        params: List[Dict[str, Any]] = action.get("params", [])
        mcp_input_schema = {
            "type": "object",
            "properties": {},
        }
        required = []
        for p in params:
            pname = p["name"]
            ptype = p["type"]
            mcp_type = "string"
            if "int" in ptype:
                mcp_type = "number"
            mcp_input_schema["properties"][pname] = {
                "type": mcp_type,
                "description": p.get("description", ""),
            }
            if p.get("required", False):
                required.append(pname)
        if required:
            mcp_input_schema["required"] = required

        tools.append({
            "name": action["name"],
            "description": f"[{action['category']}] {action['description']}",
            "inputSchema": mcp_input_schema,
        })
    return tools


async def run_mcp_server(
    cfg_path: Optional[str] = None,
    *,
    debug: bool = False,
) -> None:
    """Run the MCP server over stdio transport.

    Reads JSON-RPC requests from stdin and writes responses to stdout.
    Connects to the plmux daemon on startup.
    """
    if not is_server_alive():
        print("No plmux daemon running. Start one with: plmux", file=sys.stderr)
        sys.exit(1)

    ipc_conn, init_data = await attach_to_server()

    async def send_cmd(cmd: Dict[str, Any]) -> None:
        await ipc_conn.send_command(cmd)

    if debug:
        print(f"[mcp] Connected to plmux daemon ({len(init_data.get('pane_info', []))} panes)", file=sys.stderr)

    loop = asyncio.get_running_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    writer_transport, writer_protocol = await loop.connect_write_pipe(
        asyncio.Protocol, sys.stdout
    )

    async def send_response(response: Dict[str, Any]) -> None:
        data = (json.dumps(response, ensure_ascii=False) + "\n").encode("utf-8")
        writer_transport.write(data)
        await writer_transport.drain()

    tools_cache = _mcp_tools()

    try:
        while True:
            line = await asyncio.wait_for(reader.readline(), timeout=None)
            if not line:
                break

            raw = line.decode("utf-8", errors="replace").strip()
            if not raw:
                continue

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_id = msg.get("id")
            method = msg.get("method", "")
            params = msg.get("params", {})

            if method == "initialize":
                await send_response({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "protocolVersion": MCP_PROTOCOL_VERSION,
                        "capabilities": {
                            "tools": {},
                        },
                        "serverInfo": {
                            "name": "plmux",
                            "version": "0.1.0",
                        },
                    },
                })

            elif method == "notifications/initialized":
                pass

            elif method == "tools/list":
                await send_response({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "tools": tools_cache,
                    },
                })

            elif method == "tools/call":
                tool_name = params.get("name", "")
                tool_args = params.get("arguments", {})

                result = await handle_command_from_dict(send_cmd, None, tool_name, tool_args)

                tool_result_parts = []
                if result["success"]:
                    msg_text = result.get("message", "")
                    data = result.get("data")
                    if msg_text:
                        tool_result_parts.append(msg_text)
                    if data:
                        tool_result_parts.append(json.dumps(data, ensure_ascii=False, default=str))
                    content = "\n".join(tool_result_parts) if tool_result_parts else "ok"
                else:
                    content = result.get("message", "Failed")

                await send_response({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": content,
                            }
                        ],
                        "isError": not result["success"],
                    },
                })

            elif method == "ping":
                await send_response({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {},
                })

            else:
                await send_response({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}",
                    },
                })

    except (asyncio.CancelledError, EOFError, BrokenPipeError):
        pass
    finally:
        ipc_conn.close()
        writer_transport.close()


def main() -> None:
    asyncio.run(run_mcp_server())


if __name__ == "__main__":
    main()

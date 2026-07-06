"""REST API server for plmux AI integration.

Starts a lightweight HTTP server that exposes all plmux operations
as JSON REST endpoints.  Can run standalone (connects to an existing
plmux daemon) or embedded in the web server.

Usage:
    plmux --serve-rest
    # or:
    python -m plmux.tools.rest_server

This will start a REST API on http://127.0.0.1:9889 by default.
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any, Dict, Optional

from plmux.config.loader import load_config
from plmux.daemon.client import attach_to_server, is_server_alive

from plmux.tools.rest_commands import action_list, handle_command_from_dict


def _json_response(data: Any, status: int = 200) -> bytes:
    body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
    status_text = {200: "OK", 400: "Bad Request", 404: "Not Found", 405: "Method Not Allowed", 500: "Internal Server Error"}
    header = (
        f"HTTP/1.1 {status} {status_text.get(status, 'Unknown')}\r\n"
        f"Content-Type: application/json; charset=utf-8\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"Access-Control-Allow-Origin: *\r\n"
        f"Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS\r\n"
        f"Access-Control-Allow-Headers: Content-Type, Authorization\r\n"
        f"Connection: close\r\n\r\n"
    ).encode("utf-8")
    return header + body


def _error(msg: str, status: int = 400) -> bytes:
    return _json_response({"success": False, "error": msg}, status)


def _ok(data: Any = None, message: str = "ok") -> bytes:
    return _json_response({"success": True, "message": message, "data": data})


async def run_rest_server(
    cfg_path: Optional[str] = None,
    *,
    host: str = "127.0.0.1",
    port: int = 9889,
    debug: bool = False,
) -> None:
    """Run the REST API server.

    Connects to a running plmux daemon and exposes its operations via HTTP.
    """
    if not is_server_alive():
        print("[rest] No plmux daemon running. Start one with: plmux", file=sys.stderr)
        sys.exit(1)

    ipc_conn, init_data = await attach_to_server()
    cfg = load_config(cfg_path)

    async def send_cmd(cmd: Dict[str, Any]) -> None:
        await ipc_conn.send_command(cmd)

    async def handle_http(
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        try:
            request_line = await asyncio.wait_for(reader.readline(), timeout=10.0)
        except (asyncio.TimeoutError, Exception):
            writer.close()
            return

        request = request_line.decode("utf-8", errors="replace").strip()
        if not request:
            writer.close()
            return

        method = request.split(" ")[0] if " " in request else "GET"
        path = request.split(" ")[1] if request.count(" ") >= 1 else "/"

        headers: Dict[str, str] = {}
        body_len = 0
        while True:
            try:
                line = await asyncio.wait_for(reader.readline(), timeout=3.0)
            except (asyncio.TimeoutError, Exception):
                break
            if line in (b"\r\n", b"\n", b""):
                break
            decoded = line.decode("utf-8", errors="replace")
            if ":" in decoded:
                k, v = decoded.split(":", 1)
                headers[k.strip().lower()] = v.strip()
                if k.strip().lower() == "content-length":
                    body_len = int(v.strip())

        body = b""
        if body_len > 0:
            try:
                body = await asyncio.wait_for(reader.readexactly(body_len), timeout=5.0)
            except (asyncio.IncompleteReadError, asyncio.TimeoutError):
                pass

        resp = await _route_request(method, path, body, send_cmd, init_data, cfg)

        try:
            writer.write(resp)
            await writer.drain()
        except Exception:
            pass
        writer.close()

    server = await asyncio.start_server(handle_http, host, port)
    addr = server.sockets[0].getsockname() if server.sockets else (host, port)
    print(f"[rest] plmux REST API listening on http://{addr[0]}:{addr[1]}")
    print(f"[rest] Connected to plmux daemon ({len(init_data.get('pane_info', []))} panes)")

    try:
        async with server:
            await server.serve_forever()
    except asyncio.CancelledError:
        pass
    finally:
        ipc_conn.close()


async def _route_request(
    method: str,
    path: str,
    body: bytes,
    send_cmd,
    init_data: Dict[str, Any],
    cfg,
) -> bytes:
    if method == "OPTIONS":
        return _json_response({"success": True})

    parsed_body: Dict[str, Any] = {}
    if body and method in ("POST", "PUT"):
        try:
            parsed_body = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return _error("Invalid JSON body")

    if path == "/api" or path == "/api/" or path == "/":
        return _ok({
            "name": "plmux REST API",
            "version": "0.1.0",
            "endpoints": {
                "GET /api": "This info",
                "GET /api/actions": "List all available actions",
                "GET /api/sessions": "List sessions and panes",
                "GET /api/status": "Server status info",
                "POST /api/command": "Execute an action",
                "POST /api/command/<action>": "Execute a specific action",
            },
        })

    if path == "/api/actions":
        return _ok(action_list())

    if path == "/api/sessions" or path == "/api/panes":
        info = {
            "current_session": init_data.get("current_session", 0),
            "sessions_data": init_data.get("sessions_data", []),
            "pane_info": init_data.get("pane_info", []),
            "pane_count": init_data.get("pane_count", 0),
        }
        return _ok(info)

    if path == "/api/status":
        count = init_data.get("pane_count", 0)
        return _ok({
            "alive": True,
            "pane_count": count,
            "session_count": len(init_data.get("sessions_data", [])),
        })

    if path == "/api/command" or path.startswith("/api/command/"):
        if method != "POST":
            return _error("Use POST", 405)

        if path.startswith("/api/command/"):
            action = path[len("/api/command/"):]
            params = parsed_body.get("params", {})
        else:
            action = parsed_body.get("action", "")
            params = parsed_body.get("params", {})

        if not action:
            return _error("Missing 'action' field")

        result = await handle_command_from_dict(send_cmd, None, action, params)
        if result["success"]:
            return _ok(result["data"], result["message"])
        return _error(result["message"], status=404)

    return _error("Not found", 404)


def main() -> None:
    asyncio.run(run_rest_server())


if __name__ == "__main__":
    main()

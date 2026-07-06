"""Web client server: browser-based terminal access via WebSocket."""

from __future__ import annotations

import asyncio
import hashlib
import base64
import json
import os
import secrets
import ssl
import threading
from typing import Any, Callable, Optional
from urllib.parse import parse_qs, urlparse

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

_WS_MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

try:
    from plmux.web._c_extension import (
        FrameParser as FrameParser,
        encode_text_frame as encode_text_frame,
        encode_binary_frame as encode_binary_frame,
        encode_close_frame as encode_close_frame,
        encode_pong_frame as encode_pong_frame,
        OPCODE_TEXT as OPCODE_TEXT,
        OPCODE_BINARY as OPCODE_BINARY,
        OPCODE_CLOSE as OPCODE_CLOSE,
        OPCODE_PING as OPCODE_PING,
    )
    _HAS_C_KERNEL = FrameParser is not None
except ImportError:
    _HAS_C_KERNEL = False

if _HAS_C_KERNEL:
    pass
else:
    pass


def _load_html() -> str:
    index_path = os.path.join(_STATIC_DIR, "index.html")
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return (
            "<html><body><h1>plmux web</h1>"
            "<p>Static files not found. Check plmux/web/static/</p></body></html>"
        )


_CACHED_HTML: Optional[str] = None


def _get_html() -> str:
    global _CACHED_HTML
    if _CACHED_HTML is None:
        _CACHED_HTML = _load_html()
    return _CACHED_HTML


def reload_html() -> None:
    global _CACHED_HTML
    _CACHED_HTML = _load_html()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class TokenManager:
    def __init__(self) -> None:
        self._rw_hashes: dict[str, str] = {}
        self._ro_hashes: dict[str, str] = {}

    def generate(self, readonly: bool = False) -> str:
        raw = secrets.token_urlsafe(32)
        h = _hash_token(raw)
        if readonly:
            self._ro_hashes[h] = raw[:8]
        else:
            self._rw_hashes[h] = raw[:8]
        return raw

    def validate(self, token: str) -> Optional[str]:
        h = _hash_token(token)
        if h in self._rw_hashes:
            return "rw"
        if h in self._ro_hashes:
            return "ro"
        return None

    def revoke(self, token: str) -> bool:
        h = _hash_token(token)
        if h in self._rw_hashes:
            del self._rw_hashes[h]
            return True
        if h in self._ro_hashes:
            del self._ro_hashes[h]
            return True
        return False

    def load_config_tokens(self, tokens: list[str], readonly_tokens: list[str]) -> None:
        for t in tokens:
            h = _hash_token(t)
            self._rw_hashes[h] = t[:8]
        for t in readonly_tokens:
            h = _hash_token(t)
            self._ro_hashes[h] = t[:8]

    def list_tokens(self) -> list[dict[str, str]]:
        result: list[dict[str, str]] = []
        for h, prefix in self._rw_hashes.items():
            result.append({"prefix": prefix, "hash": h[:12] + "...", "mode": "read-write", "full_hash": h})
        for h, prefix in self._ro_hashes.items():
            result.append({"prefix": prefix, "hash": h[:12] + "...", "mode": "read-only", "full_hash": h})
        return result

    def token_count(self) -> int:
        return len(self._rw_hashes) + len(self._ro_hashes)

    def revoke_at(self, index: int) -> bool:
        tokens = self.list_tokens()
        if index < 0 or index >= len(tokens):
            return False
        h = tokens[index]["full_hash"]
        if h in self._rw_hashes:
            del self._rw_hashes[h]
            return True
        if h in self._ro_hashes:
            del self._ro_hashes[h]
            return True
        return False


class WebClientServer:
    def __init__(
        self,
        workspace: Any,
        *,
        host: str = "0.0.0.0",
        port: int = 9888,
        on_input: Optional[Callable] = None,
        tls_cert: Optional[str] = None,
        tls_key: Optional[str] = None,
        auth_enabled: bool = False,
        config_tokens: Optional[list[str]] = None,
        config_readonly_tokens: Optional[list[str]] = None,
    ) -> None:
        self.ws_ref = workspace
        self.host = host
        self.port = port
        self.on_input = on_input
        self.tls_cert = tls_cert
        self.tls_key = tls_key
        self.auth_enabled = auth_enabled
        self.token_manager = TokenManager()
        if config_tokens or config_readonly_tokens:
            self.token_manager.load_config_tokens(
                config_tokens or [], config_readonly_tokens or []
            )
        self._server: Optional[asyncio.AbstractServer] = None
        self._clients: set[_SimpleWebSocket] = set()
        self._running = False
        self._drain_tasks: list[asyncio.Task] = []
        self._drain_queue: asyncio.Queue | None = None
        self._pane_drain_queue: asyncio.Queue | None = None
        self._drain_lock = threading.Lock()

    def _build_ssl_context(self) -> Optional[ssl.SSLContext]:
        if not self.tls_cert or not self.tls_key:
            return None
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(self.tls_cert, self.tls_key)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        return ctx

    async def start(self) -> None:
        ssl_ctx = self._build_ssl_context()
        self._server = await asyncio.start_server(
            self._handle_connection, self.host, self.port, ssl=ssl_ctx
        )
        self._running = True
        self._drain_queue = asyncio.Queue()
        self._pane_drain_queue = asyncio.Queue()
        self._drain_tasks.append(asyncio.ensure_future(self._drain_loop()))
        self._drain_tasks.append(asyncio.ensure_future(self._pane_drain_loop()))
        addrs = ", ".join(str(s.getsockname()) for s in self._server.sockets)
        scheme = "https" if ssl_ctx else "http"
        print(f"[web] plmux web client listening on {scheme}://{addrs}")
        if self.auth_enabled:
            print(f"[web] authentication enabled, {len(self.token_manager._rw_hashes)} rw + {len(self.token_manager._ro_hashes)} ro tokens loaded")

    async def stop(self) -> None:
        self._running = False
        for t in self._drain_tasks:
            t.cancel()
        self._drain_tasks.clear()
        if self._drain_queue:
            while not self._drain_queue.empty():
                try:
                    self._drain_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
        if self._pane_drain_queue:
            while not self._pane_drain_queue.empty():
                try:
                    self._pane_drain_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
        for ws in list(self._clients):
            await ws.close()
        self._clients.clear()
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def broadcast(self, msg_type: str, data: dict) -> None:
        if not self._clients:
            return
        payload = json.dumps({"type": msg_type, **data})
        closed: set[_SimpleWebSocket] = set()
        for ws in self._clients:
            try:
                await ws.send(payload)
            except Exception:
                closed.add(ws)
        self._clients -= closed

    def enqueue_output(self, data: bytes) -> None:
        if self._drain_queue is None:
            return
        try:
            with self._drain_lock:
                self._drain_queue.put_nowait(data)
        except Exception:
            pass

    def enqueue_pane_output(self, pane_idx: int, data: bytes) -> None:
        if self._pane_drain_queue is None:
            return
        try:
            with self._drain_lock:
                self._pane_drain_queue.put_nowait((pane_idx, data))
        except Exception:
            pass

    async def _drain_loop(self) -> None:
        assert self._drain_queue is not None
        buf = bytearray()
        while True:
            try:
                chunk = await asyncio.wait_for(self._drain_queue.get(), timeout=0.033)
                buf.extend(chunk)
                while not self._drain_queue.empty():
                    try:
                        extra = self._drain_queue.get_nowait()
                        buf.extend(extra)
                    except asyncio.QueueEmpty:
                        break
                if buf and self._clients:
                    text = bytes(buf).decode("utf-8", errors="replace")
                    if _HAS_C_KERNEL:
                        frame_bytes = encode_text_frame(
                            json.dumps({"type": "output", "data": text})
                        )
                        closed: set[_SimpleWebSocket] = set()
                        for ws in self._clients:
                            try:
                                ws._writer.write(frame_bytes)
                                await ws._writer.drain()
                            except Exception:
                                closed.add(ws)
                        self._clients -= closed
                    else:
                        payload = json.dumps({"type": "output", "data": text})
                        closed: set[_SimpleWebSocket] = set()
                        for ws in self._clients:
                            try:
                                await ws.send(payload)
                            except Exception:
                                closed.add(ws)
                        self._clients -= closed
                buf.clear()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception:
                continue

    async def _pane_drain_loop(self) -> None:
        assert self._pane_drain_queue is not None
        pane_bufs: dict[int, bytearray] = {}
        while True:
            try:
                item = await asyncio.wait_for(self._pane_drain_queue.get(), timeout=0.033)
                pane_idx, data = item
                if pane_idx not in pane_bufs:
                    pane_bufs[pane_idx] = bytearray()
                pane_bufs[pane_idx].extend(data)
                while not self._pane_drain_queue.empty():
                    try:
                        extra_idx, extra_data = self._pane_drain_queue.get_nowait()
                        if extra_idx not in pane_bufs:
                            pane_bufs[extra_idx] = bytearray()
                        pane_bufs[extra_idx].extend(extra_data)
                    except asyncio.QueueEmpty:
                        break
                if pane_bufs and self._clients:
                    for idx, buf in pane_bufs.items():
                        if not buf:
                            continue
                        text = bytes(buf).decode("utf-8", errors="replace")
                        payload = json.dumps({"type": "pane_output", "idx": idx, "data": text})
                        closed: set[_SimpleWebSocket] = set()
                        if _HAS_C_KERNEL:
                            try:
                                frame_bytes = encode_text_frame(payload)
                                for ws in self._clients:
                                    try:
                                        ws._writer.write(frame_bytes)
                                        await ws._writer.drain()
                                    except Exception:
                                        closed.add(ws)
                            except Exception:
                                for ws in self._clients:
                                    try:
                                        await ws.send(payload)
                                    except Exception:
                                        closed.add(ws)
                        else:
                            for ws in self._clients:
                                try:
                                    await ws.send(payload)
                                except Exception:
                                    closed.add(ws)
                        self._clients -= closed
                pane_bufs.clear()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception:
                continue

    async def _handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            request_line = await asyncio.wait_for(reader.readline(), timeout=5.0)
        except (asyncio.TimeoutError, Exception):
            writer.close()
            return

        request = request_line.decode("utf-8", errors="replace").strip()
        is_ws = False
        ws_key = ""
        headers: dict[str, str] = {}
        while True:
            try:
                line = await asyncio.wait_for(reader.readline(), timeout=3.0)
            except (asyncio.TimeoutError, Exception):
                break
            if line in (b"\r\n", b"\n", b""):
                break
            decoded = line.decode("utf-8", errors="replace")
            lower = decoded.lower()
            if "upgrade: websocket" in lower:
                is_ws = True
            if lower.startswith("sec-websocket-key:"):
                ws_key = decoded.split(":", 1)[1].strip()
            if ":" in decoded:
                k, v = decoded.split(":", 1)
                headers[k.strip().lower()] = v.strip()

        parsed = urlparse(request.split(" ", 2)[1] if " " in request else "/")
        path = parsed.path
        query = parse_qs(parsed.query)

        method = request.split(" ")[0] if " " in request else "GET"
        body = b""
        content_length = int(headers.get("content-length", 0))
        if content_length > 0 and path.startswith("/api/"):
            try:
                body = await asyncio.wait_for(reader.readexactly(content_length), timeout=5.0)
            except (asyncio.IncompleteReadError, asyncio.TimeoutError):
                pass

        if is_ws and "/ws" in path:
            token_value = query.get("token", [None])[0]
            auth_mode = self._check_auth(token_value, headers)
            if self.auth_enabled and auth_mode is None:
                await self._serve_401(writer)
                return
            await self._handle_ws(reader, writer, ws_key, auth_mode)
        elif request.startswith("GET / "):
            token_value = query.get("token", [None])[0]
            auth_mode = self._check_auth(token_value, headers)
            if self.auth_enabled and auth_mode is None:
                await self._serve_401_page(writer)
                return
            await self._serve_html(writer, auth_mode)
        elif request.startswith("GET /session/"):
            token_value = query.get("token", [None])[0]
            auth_mode = self._check_auth(token_value, headers)
            if self.auth_enabled and auth_mode is None:
                await self._serve_401_page(writer)
                return
            session_name = path[len("/session/"):]
            await self._serve_html(writer, auth_mode, session=session_name)
        elif path.startswith("/api/"):
            await self._serve_api_request(method=method, path=path, body=body, headers=headers, writer=writer)
        elif request.startswith("GET /"):
            path_only = path.split("?")[0]
            if path_only.startswith("/static/"):
                await self._serve_static(writer, path_only)
            elif path_only == "/api/tokens" and self.auth_enabled:
                await self._serve_token_api(writer, headers)
            else:
                await self._serve_404(writer)
        else:
            await self._serve_404(writer)

    def _check_auth(self, token: Optional[str], headers: dict[str, str]) -> Optional[str]:
        if not self.auth_enabled:
            return "rw"
        if token:
            mode = self.token_manager.validate(token)
            if mode:
                return mode
        auth_header = headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            mode = self.token_manager.validate(auth_header[7:])
            if mode:
                return mode
        return None

    async def _serve_api_request(
        self,
        method: str,
        path: str,
        body: bytes,
        headers: dict[str, str],
        writer: asyncio.StreamWriter,
    ) -> None:
        import json as _json

        if self.auth_enabled:
            token = None
            auth_header = headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
            auth_mode = self.token_manager.validate(token) if token else None
            if auth_mode is None:
                data = self._json_resp({"success": False, "error": "unauthorized"}, 401)
                writer.write(data)
                await writer.drain()
                writer.close()
                return

        if path == "/api/tokens" and self.auth_enabled:
            await self._serve_token_api(writer, headers)
            return

        parsed_body: dict = {}
        if body and method in ("POST", "PUT"):
            try:
                parsed_body = _json.loads(body.decode("utf-8"))
            except (_json.JSONDecodeError, UnicodeDecodeError):
                data = self._json_resp({"success": False, "error": "Invalid JSON body"})
                writer.write(data)
                await writer.drain()
                writer.close()
                return

        ws = self.ws_ref
        resp = await self._handle_api_route(method, path, parsed_body, ws)
        try:
            writer.write(resp)
            await writer.drain()
        except Exception:
            pass
        writer.close()

    def _json_resp(self, data: dict, status: int = 200) -> bytes:
        import json as _json
        body = _json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
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

    async def _handle_api_route(self, method: str, path: str, parsed_body: dict, ws) -> bytes:
        from plmux.tools.rest_commands import action_list

        if method == "OPTIONS":
            return self._json_resp({"success": True})

        if path == "/api" or path == "/api/":
            return self._json_resp({
                "success": True,
                "data": {
                    "name": "plmux REST API (embedded)",
                    "endpoints": {
                        "GET /api": "This info",
                        "GET /api/actions": "List all available actions",
                        "GET /api/sessions": "List sessions",
                        "GET /api/status": "Server status",
                        "POST /api/command": "Execute action",
                    },
                },
            })

        if path == "/api/actions":
            return self._json_resp({"success": True, "data": action_list()})

        if path == "/api/sessions" or path == "/api/panes":
            info = {}
            if ws and hasattr(ws, "sessions_list"):
                sessions_data = []
                for sess in ws.sessions_list:
                    windows_data = []
                    for w in sess.windows:
                        windows_data.append({"tree": str(w.tree), "focus_pane": w.focus_pane, "pane_count": len(w.panes)})
                    sessions_data.append({
                        "name": sess.name,
                        "windows": windows_data,
                        "current_window": sess.current_window,
                        "pane_count": len(sess.sessions),
                    })
                info = {
                    "current_session": ws.current_session,
                    "sessions_data": sessions_data,
                }
            return self._json_resp({"success": True, "data": info})

        if path == "/api/status":
            alive = ws is not None
            info = {"alive": alive}
            if ws and hasattr(ws, "all_panes"):
                info["pane_count"] = len(ws.all_panes())
                info["session_count"] = len(ws.sessions_list)
            return self._json_resp({"success": True, "data": info})

        if path == "/api/command" or path.startswith("/api/command/"):
            if method != "POST":
                return self._json_resp({"success": False, "error": "Use POST"}, 405)

            if path.startswith("/api/command/"):
                action = path[len("/api/command/"):]
                params = parsed_body.get("params", {})
            else:
                action = parsed_body.get("action", "")
                params = parsed_body.get("params", {})

            if not action:
                return self._json_resp({"success": False, "error": "Missing 'action' field"})

            result = await self._dispatch_action(ws, action, params)
            if result.get("success"):
                return self._json_resp({"success": True, "data": result.get("data"), "message": result.get("message", "ok")})
            return self._json_resp({"success": False, "error": result.get("message", "Failed")}, 400)

        return self._json_resp({"success": False, "error": "Not found"}, 404)

    async def _dispatch_action(self, ws, action: str, params: dict) -> dict:
        from plmux.tools.rest_commands import _build_ipc_command

        if ws is None:
            return {"success": False, "message": "No workspace available"}

        cmd = _build_ipc_command(action, params)
        if cmd is None:
            return self._dispatch_action_direct(ws, action, params)

        _action = cmd.get("action", "")
        try:
            if _action == "split":
                ws.split(cmd.get("direction", "row"))
            elif _action == "only_pane":
                ws.only_pane()
            elif _action == "new_window":
                ws.new_window()
            elif _action == "close_window":
                ws.close_window()
            elif _action == "next_window":
                ws.next_window()
            elif _action == "prev_window":
                ws.prev_window()
            elif _action == "goto_window":
                ws.goto_window(cmd.get("index", 0))
            elif _action == "set_focus_pane":
                ws.set_focus_pane(cmd.get("index", 0))
            elif _action == "focus_direction":
                ws.focus_direction(cmd.get("direction", "left"))
            elif _action == "kill_pane":
                idx = cmd.get("pane_index")
                if idx is not None:
                    ws.remove_pane(idx)
                else:
                    ws.remove_pane(ws.focus_pane)
            elif _action == "swap_pane":
                ws.swap_pane(cmd.get("direction", "up"))
            elif _action == "break_pane":
                ws.break_pane()
            elif _action == "join_pane":
                ws.join_pane(cmd.get("direction", "row"))
            elif _action == "respawn_pane":
                ws.respawn_pane(cmd.get("pane_index"))
            elif _action == "resize_pane":
                ws.resize_pane(cmd.get("direction", "left"))
            elif _action == "toggle_zoom":
                ws.toggle_zoom()
            elif _action == "rotate_panes":
                ws.rotate_panes(cmd.get("direction", "up"))
            elif _action == "cycle_layout":
                ws.cycle_layout()
            elif _action == "send_keys":
                ws.send_keys(cmd.get("text", ""))
            elif _action == "rename_window":
                ws.rename_window(cmd.get("name", ""))
            elif _action == "rename_session":
                ws.rename_session(cmd.get("name", ""))
            elif _action == "new_session":
                ws.new_session(cmd.get("name", ""))
            elif _action == "switch_session":
                ws.switch_session(cmd.get("index", 0))
            elif _action == "kill_session":
                ws.kill_session(cmd.get("index"))
            elif _action == "next_session":
                ws.next_session()
            elif _action == "prev_session":
                ws.prev_session()
            elif _action == "apply_layout_template":
                ws.apply_layout_template(cmd.get("name", ""))
            elif _action == "display_panes":
                pass
            else:
                return {"success": False, "message": f"Unknown action: {_action}"}
            return {"success": True, "message": f"Action '{action}' executed", "data": cmd}
        except Exception as e:
            return {"success": False, "message": f"Action failed: {e}"}

    def _dispatch_action_direct(self, ws, action: str, params: dict) -> dict:
        handlers = {
            "set_option": lambda: None,
            "show_options": lambda: None,
            "reload_config": lambda: None,
            "list_themes": lambda: None,
            "set_theme": lambda: None,
            "server_status": lambda: None,
            "help": lambda: None,
        }
        handler = handlers.get(action)
        if handler:
            try:
                handler()
                return {"success": True, "message": f"Action '{action}' dispatched"}
            except Exception as e:
                return {"success": False, "message": str(e)}
        return {"success": False, "message": f"Unknown action: {action}"}

    async def _serve_html(
        self,
        writer: asyncio.StreamWriter,
        auth_mode: Optional[str] = None,
        session: Optional[str] = None,
    ) -> None:
        html = _get_html()
        inject_parts: list[str] = []
        if auth_mode:
            inject_parts.append(f'window.__PLMUX_AUTH_MODE="{auth_mode}";')
        if session:
            inject_parts.append(f'window.__PLMUX_SESSION="{session}";')
        if inject_parts:
            script_tag = "<script>" + "".join(inject_parts) + "</script>"
            html = html.replace("</head>", script_tag + "</head>")
        body = html.encode("utf-8")
        header = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/html; charset=utf-8\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Connection: close\r\n\r\n"
        ).encode("utf-8")
        writer.write(header + body)
        await writer.drain()
        writer.close()

    _MIME_TYPES = {
        ".js": "application/javascript; charset=utf-8",
        ".mjs": "application/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".html": "text/html; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".png": "image/png",
        ".ico": "image/x-icon",
        ".svg": "image/svg+xml",
    }

    async def _serve_static(self, writer: asyncio.StreamWriter, url_path: str) -> None:
        rel_path = url_path.lstrip("/")
        if rel_path.startswith("static/"):
            rel_path = rel_path[len("static/"):]
        file_path = os.path.join(_STATIC_DIR, rel_path)

        if not os.path.isfile(file_path):
            await self._serve_404(writer)
            return

        ext = os.path.splitext(file_path)[1].lower()
        content_type = self._MIME_TYPES.get(ext, "application/octet-stream")

        try:
            with open(file_path, "rb") as f:
                body = f.read()
        except OSError:
            await self._serve_404(writer)
            return

        header = (
            "HTTP/1.1 200 OK\r\n"
            f"Content-Type: {content_type}\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Cache-Control: no-cache\r\n"
            "Connection: close\r\n\r\n"
        ).encode("utf-8")
        writer.write(header + body)
        await writer.drain()
        writer.close()

    async def _serve_404(self, writer: asyncio.StreamWriter) -> None:
        body = b"Not Found"
        header = (
            "HTTP/1.1 404 Not Found\r\n"
            "Content-Type: text/plain\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Connection: close\r\n\r\n"
        ).encode("utf-8")
        writer.write(header + body)
        await writer.drain()
        writer.close()

    async def _serve_401(self, writer: asyncio.StreamWriter) -> None:
        body = b'{"error":"unauthorized"}'
        header = (
            "HTTP/1.1 401 Unauthorized\r\n"
            "Content-Type: application/json\r\n"
            "WWW-Authenticate: Bearer\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Connection: close\r\n\r\n"
        ).encode("utf-8")
        writer.write(header + body)
        await writer.drain()
        writer.close()

    async def _serve_401_page(self, writer: asyncio.StreamWriter) -> None:
        body = (
            "<html><head><title>401 Unauthorized</title></head>"
            "<body style='background:#1d2021;color:#ebdbb2;display:flex;"
            "justify-content:center;align-items:center;height:100vh;"
            "font-family:monospace'>"
            "<div style='text-align:center'>"
            "<h1 style='color:#f92672'>401 Unauthorized</h1>"
            "<p>Authentication required. Provide a valid token via "
            "<code>?token=...</code> query parameter.</p>"
            "</div></body></html>"
        ).encode("utf-8")
        header = (
            "HTTP/1.1 401 Unauthorized\r\n"
            "Content-Type: text/html; charset=utf-8\r\n"
            "WWW-Authenticate: Bearer\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Connection: close\r\n\r\n"
        ).encode("utf-8")
        writer.write(header + body)
        await writer.drain()
        writer.close()

    async def _serve_token_api(self, writer: asyncio.StreamWriter, headers: dict[str, str]) -> None:
        auth_header = headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            await self._serve_401(writer)
            return
        mode = self.token_manager.validate(auth_header[7:])
        if mode != "rw":
            await self._serve_401(writer)
            return
        tokens = self.token_manager.list_tokens()
        body = json.dumps({"tokens": tokens}).encode("utf-8")
        header = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Connection: close\r\n\r\n"
        ).encode("utf-8")
        writer.write(header + body)
        await writer.drain()
        writer.close()

    async def _handle_ws(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        ws_key: str,
        auth_mode: Optional[str] = None,
    ) -> None:
        ws = _SimpleWebSocket(reader, writer)
        ws._ws_key = ws_key
        ws._auth_mode = auth_mode or "rw"
        try:
            await ws.do_handshake()
        except Exception:
            writer.close()
            return

        self._clients.add(ws)
        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                    await self._process_message(ws, msg)
                except json.JSONDecodeError:
                    if raw and self.on_input and ws._auth_mode == "rw":
                        self.on_input(raw)
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            self._clients.discard(ws)
            if not self._clients and self.ws_ref:
                self.ws_ref._web_term_rows = None
                self.ws_ref._web_term_cols = None
            try:
                await ws.close()
            except Exception:
                pass

    async def _process_message(self, ws: _SimpleWebSocket, msg: dict) -> None:
        msg_type = msg.get("type", "")
        is_readonly = getattr(ws, "_auth_mode", "rw") == "ro"

        if msg_type == "input":
            if is_readonly:
                return
            data = msg.get("data", "")
            if data and self.on_input:
                self.on_input(data)
        elif msg_type == "key":
            if is_readonly:
                return
            key_str = _web_key_to_terminal(msg)
            if key_str and self.on_input:
                self.on_input(key_str)
        elif msg_type == "paste":
            if is_readonly:
                return
            text = msg.get("text", "")
            if text and self.on_input:
                self.on_input(text)
        elif msg_type == "ready":
            cols = msg.get("cols", 80)
            rows = msg.get("rows", 24)
            ws._plmux_cols = cols
            ws._plmux_rows = rows
            if self.ws_ref:
                self.ws_ref._web_term_cols = cols
                self.ws_ref._web_term_rows = rows
                self.ws_ref._overlay_cols = msg.get("overlay_cols", 80)
                self.ws_ref._overlay_rows = msg.get("overlay_rows", 26)
                if hasattr(self.ws_ref, "sessions"):
                    for session in self.ws_ref.sessions:
                        try:
                            session.resize(rows, cols)
                        except Exception:
                            pass
                    for i, s in enumerate(self.ws_ref.sessions):
                        try:
                            content = s.build_render_text(draw_cursor=(i == self.ws_ref.focus_pane))
                            snapshot_lines = []
                            for line_ansi in content._lines:
                                snapshot_lines.append(line_ansi)
                            snapshot_data = "\r\n".join(snapshot_lines)
                            cursor_y = s.screen.cursor.y
                            cursor_x = s.screen.cursor.x
                            reposition = f"\x1b[{cursor_y + 1};{cursor_x + 1}H"
                            await self.broadcast("pane_snapshot", {
                                "idx": i,
                                "data": snapshot_data + reposition,
                                "cursor": [cursor_y, cursor_x],
                            })
                        except Exception:
                            pass
                    try:
                        from plmux.web.server import _build_layout_msg
                        layout_msg = _build_layout_msg(self.ws_ref)
                        await self.broadcast("layout", layout_msg)
                    except Exception:
                        pass
        elif msg_type == "resize":
            cols = msg.get("cols", 80)
            rows = msg.get("rows", 24)
            ws._plmux_cols = cols
            ws._plmux_rows = rows
            if self.ws_ref:
                self.ws_ref._web_term_cols = cols
                self.ws_ref._web_term_rows = rows
                if hasattr(self.ws_ref, "sessions"):
                    for session in self.ws_ref.sessions:
                        try:
                            session.resize(rows, cols)
                        except Exception:
                            pass
        elif msg_type == "focus":
            if is_readonly:
                return
            pane_idx = msg.get("idx", -1)
            if self.ws_ref and pane_idx >= 0:
                try:
                    win = self.ws_ref._window()
                    if 0 <= pane_idx < len(win.panes):
                        self.ws_ref.focus_pane = pane_idx
                        import plmux.web.server as srv
                        srv._last_layout_sig = ""
                except Exception:
                    pass
        elif msg_type == "resize_pane":
            if is_readonly:
                return
            direction = msg.get("direction", "")
            if self.ws_ref and direction:
                try:
                    self.ws_ref.resize_pane(direction)
                    import plmux.web.server as srv
                    srv._last_layout_sig = ""
                except Exception:
                    pass
        elif msg_type == "overlay_resize":
            cols = msg.get("cols", 80)
            rows = msg.get("rows", 26)
            if self.ws_ref:
                self.ws_ref._overlay_cols = cols
                self.ws_ref._overlay_rows = rows


def _web_key_to_terminal(msg: dict) -> str:
    key = msg.get("key", "")
    code = msg.get("code", "")
    ctrl = msg.get("ctrl", False)
    alt = msg.get("alt", False)
    msg.get("shift", False)

    raw = msg.get("raw", "")
    if raw:
        return raw

    kitty = msg.get("kitty", "")
    if kitty:
        return kitty

    if ctrl and not alt:
        ctrl_map = {
            "a": "\x01", "b": "\x02", "c": "\x03", "d": "\x04",
            "e": "\x05", "f": "\x06", "g": "\x07", "h": "\x08",
            "i": "\x09", "j": "\x0a", "k": "\x0b", "l": "\x0c",
            "m": "\x0d", "n": "\x0e", "o": "\x0f", "p": "\x10",
            "q": "\x11", "r": "\x12", "s": "\x13", "t": "\x14",
            "u": "\x15", "v": "\x16", "w": "\x17", "x": "\x18",
            "y": "\x19", "z": "\x1a",
            "[": "\x1b", "]": "\x1d", "\\": "\x1c",
            ";": "\x1b", "'": "\x1b", " ": "\x00",
            ",": "\x1c", "/": "\x1f", "`": "\x1e",
            "2": "\x00", "6": "\x1e", "-": "\x1f", "=": "\x1d",
        }
        k = key.lower()
        if k in ctrl_map:
            return ctrl_map[k]

    if ctrl and alt:
        k = key.lower()
        if len(k) == 1 and "a" <= k <= "z":
            return "\x1b" + chr(ord(k) - ord("a") + 1)

    if alt and not ctrl:
        if len(key) == 1:
            return "\x1b" + key.lower()
        alt_special = {
            "ArrowUp": "\x1b[1;3A",
            "ArrowDown": "\x1b[1;3B",
            "ArrowRight": "\x1b[1;3C",
            "ArrowLeft": "\x1b[1;3D",
            "Home": "\x1b[1;3H",
            "End": "\x1b[1;3F",
            "Delete": "\x1b[3;3~",
            "Insert": "\x1b[2;3~",
            "PageUp": "\x1b[5;3~",
            "PageDown": "\x1b[6;3~",
            "Backspace": "\x1b\x7f",
            "Tab": "\x1b\t",
            "Enter": "\x1b\r",
            "Escape": "\x1b\x1b",
        }
        if key in alt_special:
            return alt_special[key]
        return "\x1b" + key.lower()

    special = {
        "ArrowUp": "\x1b[A",
        "ArrowDown": "\x1b[B",
        "ArrowRight": "\x1b[C",
        "ArrowLeft": "\x1b[D",
        "Home": "\x1b[H",
        "End": "\x1b[F",
        "Delete": "\x1b[3~",
        "Insert": "\x1b[2~",
        "PageUp": "\x1b[5~",
        "PageDown": "\x1b[6~",
        "Backspace": "\x7f",
        "Tab": "\t",
        "Escape": "\x1b",
        "Enter": "\r",
    }

    if key in special:
        return special[key]

    if code in special:
        return special[code]

    if key.startswith("F") and key[1:].isdigit():
        num = int(key[1:])
        if 1 <= num <= 4:
            return f"\x1b[{num + 10}~"
        elif 5 <= num <= 12:
            return f"\x1b[{num + 11}~"

    if len(key) == 1:
        return key

    return ""


class _SimpleWebSocket:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self._reader = reader
        self._writer = writer
        self._plmux_cols = 80
        self._plmux_rows = 24
        self._ws_key = ""
        self._c_parser = FrameParser() if _HAS_C_KERNEL else None
        self._read_buf = bytearray()

    async def do_handshake(self) -> None:
        key = self._ws_key
        if not key:
            raise ValueError("Missing WebSocket key")
        accept = base64.b64encode(
            hashlib.sha1((key + _WS_MAGIC).encode()).digest()
        ).decode()

        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
        )
        self._writer.write(response.encode("utf-8"))
        await self._writer.drain()

    def __aiter__(self):
        return self

    async def __anext__(self) -> str:
        while True:
            data = await self._recv_frame()
            if data is None:
                raise StopAsyncIteration
            return data

    async def _recv_frame(self) -> Optional[str]:
        if _HAS_C_KERNEL and self._c_parser is not None:
            return await self._recv_frame_c()

        try:
            head = await self._reader.readexactly(2)
        except (asyncio.IncompleteReadError, ConnectionError):
            return None

        opcode = head[0] & 0x0F
        masked = (head[1] & 0x80) != 0
        length = head[1] & 0x7F

        if length == 126:
            ext = await self._reader.readexactly(2)
            length = int.from_bytes(ext, "big")
        elif length == 127:
            ext = await self._reader.readexactly(8)
            length = int.from_bytes(ext, "big")

        mask = b""
        if masked:
            mask = await self._reader.readexactly(4)

        payload = await self._reader.readexactly(length)
        if masked and mask:
            payload = bytes(payload[i] ^ mask[i % 4] for i in range(len(payload)))

        if opcode == 0x8:
            return None
        if opcode == 0x9:
            await self._send_frame(0xA, payload)
            return await self._recv_frame()

        return payload.decode("utf-8", errors="replace")

    async def _recv_frame_c(self) -> Optional[str]:
        assert self._c_parser is not None
        while True:
            frames = self._c_parser.parse()
            if frames:
                for frame_tuple in frames:
                    opcode = frame_tuple[0]
                    payload = frame_tuple[1]

                    if opcode == 0x8:
                        return None
                    if opcode == 0x9:
                        if isinstance(payload, str):
                            pong_data = payload.encode("utf-8")
                        elif isinstance(payload, bytes):
                            pong_data = payload
                        else:
                            pong_data = b""
                        await self._send_frame(0xA, pong_data)
                        continue

                    if isinstance(payload, str):
                        return payload
                    elif isinstance(payload, bytes):
                        return payload.decode("utf-8", errors="replace")
                    else:
                        return str(payload)

            try:
                chunk = await self._reader.read(65536)
            except (asyncio.IncompleteReadError, ConnectionError):
                return None
            if not chunk:
                return None
            self._c_parser.feed(chunk)

    async def send(self, data: str) -> None:
        if _HAS_C_KERNEL:
            try:
                frame_bytes = encode_text_frame(data)
                self._writer.write(frame_bytes)
                await self._writer.drain()
                return
            except Exception:
                pass
        await self._send_frame(0x1, data.encode("utf-8"))

    async def close(self) -> None:
        try:
            if _HAS_C_KERNEL:
                frame_bytes = encode_close_frame()
                self._writer.write(frame_bytes)
                await self._writer.drain()
            else:
                await self._send_frame(0x8, b"")
        except Exception:
            pass
        try:
            self._writer.close()
        except Exception:
            pass

    async def _send_frame(self, opcode: int, payload: bytes) -> None:
        frame = bytearray()
        frame.append(0x80 | opcode)
        length = len(payload)
        if length < 126:
            frame.append(length)
        elif length < 65536:
            frame.append(126)
            frame.extend(length.to_bytes(2, "big"))
        else:
            frame.append(127)
            frame.extend(length.to_bytes(8, "big"))
        frame.extend(payload)
        self._writer.write(bytes(frame))
        await self._writer.drain()

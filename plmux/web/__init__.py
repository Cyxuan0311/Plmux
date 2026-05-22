"""Web client server: browser-based terminal access via WebSocket."""

from __future__ import annotations

import asyncio
import hashlib
import base64
import json
import os
import threading
from typing import Any, Callable, Optional

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


class WebClientServer:
    def __init__(
        self,
        workspace: Any,
        *,
        host: str = "0.0.0.0",
        port: int = 9888,
        on_input: Optional[Callable] = None,
    ) -> None:
        self.ws_ref = workspace
        self.host = host
        self.port = port
        self.on_input = on_input
        self._server: Optional[asyncio.AbstractServer] = None
        self._clients: set[_SimpleWebSocket] = set()
        self._running = False
        self._drain_tasks: list[asyncio.Task] = []
        self._drain_queue: asyncio.Queue | None = None
        self._pane_drain_queue: asyncio.Queue | None = None
        self._drain_lock = threading.Lock()

    async def start(self) -> None:
        self._server = await asyncio.start_server(
            self._handle_connection, self.host, self.port
        )
        self._running = True
        self._drain_queue = asyncio.Queue()
        self._pane_drain_queue = asyncio.Queue()
        self._drain_tasks.append(asyncio.ensure_future(self._drain_loop()))
        self._drain_tasks.append(asyncio.ensure_future(self._pane_drain_loop()))
        addrs = ", ".join(str(s.getsockname()) for s in self._server.sockets)
        print(f"[web] plmux web client listening on http://{addrs}")

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
        while True:
            try:
                line = await asyncio.wait_for(reader.readline(), timeout=3.0)
            except (asyncio.TimeoutError, Exception):
                break
            if line in (b"\r\n", b"\n", b""):
                break
            decoded = line.decode("utf-8", errors="replace").lower()
            if "upgrade: websocket" in decoded:
                is_ws = True
            if decoded.startswith("sec-websocket-key:"):
                ws_key = line.decode("utf-8", errors="replace").split(":", 1)[1].strip()

        if is_ws and "/ws" in request:
            await self._handle_ws(reader, writer, ws_key)
        elif request.startswith("GET / "):
            await self._serve_html(writer)
        elif request.startswith("GET /"):
            path = request.split(" ", 2)[1].split("?")[0]
            if path.startswith("/static/"):
                await self._serve_static(writer, path)
            else:
                await self._serve_404(writer)
        else:
            await self._serve_404(writer)

    async def _serve_html(self, writer: asyncio.StreamWriter) -> None:
        body = _get_html().encode("utf-8")
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

    async def _handle_ws(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, ws_key: str
    ) -> None:
        ws = _SimpleWebSocket(reader, writer)
        ws._ws_key = ws_key
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
                    if raw and self.on_input:
                        self.on_input(raw)
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            self._clients.discard(ws)
            try:
                await ws.close()
            except Exception:
                pass

    async def _process_message(self, ws: _SimpleWebSocket, msg: dict) -> None:
        msg_type = msg.get("type", "")

        if msg_type == "input":
            data = msg.get("data", "")
            if data and self.on_input:
                self.on_input(data)
        elif msg_type == "key":
            key_str = _web_key_to_terminal(msg)
            if key_str and self.on_input:
                self.on_input(key_str)
        elif msg_type == "paste":
            text = msg.get("text", "")
            if text and self.on_input:
                self.on_input(text)
        elif msg_type == "ready":
            cols = msg.get("cols", 80)
            rows = msg.get("rows", 24)
            ws._plmux_cols = cols
            ws._plmux_rows = rows
            if self.ws_ref and hasattr(self.ws_ref, "sessions"):
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
            if self.ws_ref and hasattr(self.ws_ref, "sessions"):
                for session in self.ws_ref.sessions:
                    try:
                        session.resize(rows, cols)
                    except Exception:
                        pass


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

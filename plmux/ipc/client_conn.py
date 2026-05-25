"""IPC Client-side connection handler.

Connects to the server, receives PTY output and state updates,
sends key/mouse/resize events to the server.
"""

from __future__ import annotations

import asyncio
import json
import struct
from typing import Any, Callable, Dict, List, Optional, Tuple

from plmux.ipc import (
    FrameReader,
    FrameWriter,
    MSG_INIT,
    MSG_PANE_OUTPUT,
    MSG_STATE_UPDATE,
    MSG_PANE_CLOSED,
    MSG_BELL,
    MSG_KEY,
    MSG_RESIZE,
    MSG_COMMAND,
    MSG_MOUSE,
    MSG_DETACH,
    HEADER_SIZE,
    parse_pane_output,
    parse_pane_closed,
    parse_bell,
)


class ServerConnection:
    """Client-side connection to the plmux server."""

    def __init__(
        self,
        sock: Any,
        loop: asyncio.AbstractEventLoop,
        *,
        on_pane_output: Optional[Callable[[int, bytes], None]] = None,
        on_state_update: Optional[Callable[[dict], None]] = None,
        on_pane_closed: Optional[Callable[[int], None]] = None,
        on_bell: Optional[Callable[[int], None]] = None,
    ) -> None:
        self._sock = sock
        self._loop = loop
        self._reader = FrameReader()
        self._writer = FrameWriter()
        self._closed = False
        self._on_pane_output = on_pane_output
        self._on_state_update = on_state_update
        self._on_pane_closed = on_pane_closed
        self._on_bell = on_bell
        self._init_data: Optional[dict] = None
        self._write_lock = asyncio.Lock()

    async def recv_init(self) -> dict:
        while not self._closed:
            try:
                chunk = await self._loop.sock_recv(self._sock, 65536)
            except (ConnectionResetError, BrokenPipeError, OSError):
                raise ConnectionError("Server closed connection")
            if not chunk:
                raise ConnectionError("Server closed connection")

            self._reader.feed(chunk)

            frame = self._reader.read_one()
            if frame is not None:
                msg_type, payload = frame
                if msg_type == MSG_INIT:
                    self._init_data = json.loads(payload.decode("utf-8"))
                    return self._init_data
                else:
                    await self._handle_message(msg_type, payload)

        raise ConnectionError("Connection closed before INIT")

    async def recv_loop(self) -> None:
        try:
            while not self._closed:
                try:
                    chunk = await self._loop.sock_recv(self._sock, 65536)
                except (ConnectionResetError, BrokenPipeError, OSError):
                    break
                if not chunk:
                    break

                self._reader.feed(chunk)
                frames = self._reader.read_all()

                for msg_type, payload in frames:
                    await self._handle_message(msg_type, payload)
        finally:
            self._closed = True

    async def _handle_message(self, msg_type: int, payload: bytes) -> None:
        if msg_type == MSG_PANE_OUTPUT:
            pane_idx, data = parse_pane_output(payload)
            if self._on_pane_output:
                self._on_pane_output(pane_idx, data)
        elif msg_type == MSG_STATE_UPDATE:
            try:
                state = json.loads(payload.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return
            if self._on_state_update:
                self._on_state_update(state)
        elif msg_type == MSG_PANE_CLOSED:
            pane_idx = parse_pane_closed(payload)
            if self._on_pane_closed:
                self._on_pane_closed(pane_idx)
        elif msg_type == MSG_BELL:
            pane_idx = parse_bell(payload)
            if self._on_bell:
                self._on_bell(pane_idx)

    async def send_key(self, pane_idx: int, data: bytes) -> None:
        frame = self._writer.key(pane_idx, data)
        await self._send_raw(frame)

    async def send_resize(self, rows: int, cols: int) -> None:
        frame = self._writer.resize(rows, cols)
        await self._send_raw(frame)

    async def send_command(self, cmd: dict) -> None:
        payload = json.dumps(cmd, ensure_ascii=False).encode("utf-8")
        frame = self._writer.command(payload)
        await self._send_raw(frame)

    async def send_mouse(self, mouse: dict) -> None:
        payload = json.dumps(mouse, ensure_ascii=False).encode("utf-8")
        frame = self._writer.mouse(payload)
        await self._send_raw(frame)

    async def send_detach(self) -> None:
        frame = self._writer.detach()
        await self._send_raw(frame)

    async def _send_raw(self, data: bytes) -> None:
        if self._closed:
            return
        async with self._write_lock:
            try:
                await self._loop.sock_sendall(self._sock, data)
            except (BrokenPipeError, ConnectionResetError, OSError):
                self._closed = True

    @property
    def closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        self._closed = True
        try:
            self._sock.close()
        except OSError:
            pass

"""IPC Server-side connection handler.

Manages a single client connection: sends PTY output and state updates
to the client, receives key/mouse/resize events from the client.
"""

from __future__ import annotations

import asyncio
import json
import struct
from typing import Any, Callable, Dict, List, Optional

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
    parse_key,
    parse_resize,
    parse_pane_closed,
)
from plmux.terminal.session import TerminalSession


class ClientConnection:
    """Represents one attached client on the server side."""

    def __init__(
        self,
        sock: Any,
        loop: asyncio.AbstractEventLoop,
        *,
        on_key: Optional[Callable[[int, bytes], None]] = None,
        on_resize: Optional[Callable[[int, int], None]] = None,
        on_command: Optional[Callable[[dict], None]] = None,
        on_mouse: Optional[Callable[[dict], None]] = None,
        on_detach: Optional[Callable[[], None]] = None,
    ) -> None:
        self._sock = sock
        self._loop = loop
        self._reader = FrameReader()
        self._writer = FrameWriter()
        self._closed = False
        self._on_key = on_key
        self._on_resize = on_resize
        self._on_command = on_command
        self._on_mouse = on_mouse
        self._on_detach = on_detach
        self._write_lock = asyncio.Lock()

    async def send_init(self, state_data: dict) -> None:
        payload = json.dumps(state_data, ensure_ascii=False).encode("utf-8")
        frame = self._writer.init(payload)
        await self._send_raw(frame)

    async def send_pane_output(self, pane_idx: int, data: bytes) -> None:
        frame = self._writer.pane_output(pane_idx, data)
        await self._send_raw(frame)

    async def send_state_update(self, state_data: dict) -> None:
        payload = json.dumps(state_data, ensure_ascii=False).encode("utf-8")
        frame = self._writer.state_update(payload)
        await self._send_raw(frame)

    async def send_pane_closed(self, pane_idx: int) -> None:
        frame = self._writer.pane_closed(pane_idx)
        await self._send_raw(frame)

    async def send_bell(self, pane_idx: int) -> None:
        frame = self._writer.bell(pane_idx)
        await self._send_raw(frame)

    async def _send_raw(self, data: bytes) -> None:
        if self._closed:
            return
        async with self._write_lock:
            try:
                await self._loop.sock_sendall(self._sock, data)
            except (BrokenPipeError, ConnectionResetError, OSError):
                self._closed = True

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
            if self._on_detach:
                self._on_detach()

    async def _handle_message(self, msg_type: int, payload: bytes) -> None:
        if msg_type == MSG_KEY:
            pane_idx, data = parse_key(payload)
            if self._on_key:
                self._on_key(pane_idx, data)
        elif msg_type == MSG_RESIZE:
            rows, cols = parse_resize(payload)
            if self._on_resize:
                self._on_resize(rows, cols)
        elif msg_type == MSG_COMMAND:
            try:
                cmd = json.loads(payload.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return
            if self._on_command:
                self._on_command(cmd)
        elif msg_type == MSG_MOUSE:
            try:
                mouse = json.loads(payload.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return
            if self._on_mouse:
                self._on_mouse(mouse)
        elif msg_type == MSG_DETACH:
            self._closed = True
            if self._on_detach:
                self._on_detach()

    @property
    def closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        self._closed = True
        try:
            self._sock.close()
        except OSError:
            pass

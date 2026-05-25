"""Binary IPC protocol: frame encoding/decoding and message type definitions.

Frame format
------------
    [4 bytes: payload length (big-endian uint32)]
    [1 byte : message type (uint8)]
    [N bytes: payload]

The 4-byte length field counts bytes *after* itself, i.e. 1 (type) + len(payload).

Message types
-------------
Server → Client (0x00-0x7F):
    0x01  INIT           Full state snapshot (JSON) sent on first connect
    0x02  PANE_OUTPUT    Raw PTY output for a pane
    0x03  STATE_UPDATE   Layout / focus / session change (JSON)
    0x04  PANE_CLOSED    A pane has exited
    0x05  BELL           Bell / alert for a pane

Client → Server (0x80-0xFF):
    0x80  KEY            Key input bytes for a pane
    0x81  RESIZE         Terminal resize event
    0x82  COMMAND        Execute a plmux command (JSON)
    0x83  MOUSE          Mouse event (JSON)
    0x84  DETACH         Client is detaching
"""

from __future__ import annotations

import struct
from typing import Optional, Tuple


class MsgType:
    INIT: int = 0x01
    PANE_OUTPUT: int = 0x02
    STATE_UPDATE: int = 0x03
    PANE_CLOSED: int = 0x04
    BELL: int = 0x05

    KEY: int = 0x80
    RESIZE: int = 0x81
    COMMAND: int = 0x82
    MOUSE: int = 0x83
    DETACH: int = 0x84


HEADER_SIZE = 5


def encode_frame(msg_type: int, payload: bytes = b"") -> bytes:
    length = 1 + len(payload)
    return struct.pack("!IB", length, msg_type) + payload


def decode_frame(data: bytes) -> Optional[Tuple[int, bytes, int]]:
    if len(data) < HEADER_SIZE:
        return None
    length = struct.unpack("!I", data[:4])[0]
    total = 4 + length
    if len(data) < total:
        return None
    msg_type = data[4]
    payload = data[5:total]
    return msg_type, payload, total


class FrameReader:
    """Incremental frame reader that accumulates bytes and yields frames."""

    __slots__ = ("_buf",)

    def __init__(self) -> None:
        self._buf = bytearray()

    def feed(self, data: bytes) -> None:
        self._buf.extend(data)

    def read_one(self) -> Optional[Tuple[int, bytes]]:
        result = decode_frame(bytes(self._buf))
        if result is None:
            return None
        msg_type, payload, total = result
        self._buf = self._buf[total:]
        return msg_type, payload

    def read_all(self) -> list[Tuple[int, bytes]]:
        frames: list[Tuple[int, bytes]] = []
        while True:
            f = self.read_one()
            if f is None:
                break
            frames.append(f)
        return frames

    @property
    def pending(self) -> int:
        return len(self._buf)


class FrameWriter:
    """Helper that encodes messages into frame bytes."""

    __slots__ = ()

    def init(self, payload: bytes) -> bytes:
        return encode_frame(MsgType.INIT, payload)

    def pane_output(self, pane_idx: int, data: bytes) -> bytes:
        header = struct.pack("!H", pane_idx)
        return encode_frame(MsgType.PANE_OUTPUT, header + data)

    def state_update(self, payload: bytes) -> bytes:
        return encode_frame(MsgType.STATE_UPDATE, payload)

    def pane_closed(self, pane_idx: int) -> bytes:
        return encode_frame(MsgType.PANE_CLOSED, struct.pack("!H", pane_idx))

    def bell(self, pane_idx: int) -> bytes:
        return encode_frame(MsgType.BELL, struct.pack("!H", pane_idx))

    def key(self, pane_idx: int, data: bytes) -> bytes:
        header = struct.pack("!H", pane_idx)
        return encode_frame(MsgType.KEY, header + data)

    def resize(self, rows: int, cols: int) -> bytes:
        return encode_frame(MsgType.RESIZE, struct.pack("!HH", rows, cols))

    def command(self, payload: bytes) -> bytes:
        return encode_frame(MsgType.COMMAND, payload)

    def mouse(self, payload: bytes) -> bytes:
        return encode_frame(MsgType.MOUSE, payload)

    def detach(self) -> bytes:
        return encode_frame(MsgType.DETACH)


def parse_pane_output(payload: bytes) -> Tuple[int, bytes]:
    pane_idx = struct.unpack("!H", payload[:2])[0]
    data = payload[2:]
    return pane_idx, data


def parse_key(payload: bytes) -> Tuple[int, bytes]:
    pane_idx = struct.unpack("!H", payload[:2])[0]
    data = payload[2:]
    return pane_idx, data


def parse_resize(payload: bytes) -> Tuple[int, int]:
    rows, cols = struct.unpack("!HH", payload[:4])
    return rows, cols


def parse_pane_closed(payload: bytes) -> int:
    return struct.unpack("!H", payload[:2])[0]


def parse_bell(payload: bytes) -> int:
    return struct.unpack("!H", payload[:2])[0]

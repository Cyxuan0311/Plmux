"""Daemon client: connect, health check, kill, and IPC attach operations."""

from __future__ import annotations

import asyncio
import os
import socket
import struct
from typing import List, Tuple

from plmux.daemon.state import ServerState, deserialize_state
from plmux.daemon.transport import (
    is_windows,
    read_port_file,
    remove_port_file,
    pid_path,
    socket_path,
    remove_socket_file,
    remove_pid_file,
    recv_fds,
)
from plmux.ipc.client_conn import ServerConnection


def is_server_alive() -> bool:
    if is_windows():
        port = read_port_file()
        if port is None:
            return False
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                s.connect(("127.0.0.1", port))
            return True
        except (OSError, ConnectionRefusedError, socket.timeout):
            remove_port_file()
            return False

    if not os.path.exists(pid_path()):
        return False
    try:
        with open(pid_path()) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        remove_pid_file()
        remove_socket_file()
        return False


def kill_server() -> bool:
    if is_windows():
        port = read_port_file()
        if port is None:
            return False
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                s.connect(("127.0.0.1", port))
                s.sendall(b"SHUTDOWN")
        except OSError:
            pass
        remove_port_file()
        return True

    if not os.path.exists(pid_path()):
        return False
    try:
        with open(pid_path()) as f:
            pid = int(f.read().strip())
        os.kill(pid, 15)
        return True
    except (OSError, ValueError):
        return False


def connect_ipc() -> Tuple[socket.socket, asyncio.AbstractEventLoop]:
    """Connect to the daemon server and return (socket, event_loop)."""
    loop = asyncio.get_event_loop()

    if is_windows():
        port = read_port_file()
        if port is None:
            raise ConnectionError("No plmux server port found")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect(("127.0.0.1", port))
    else:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(socket_path())

    sock.setblocking(False)
    return sock, loop


async def attach_to_server() -> Tuple[ServerConnection, dict]:
    """Connect to the daemon and receive INIT data. Returns (conn, init_data)."""
    sock, loop = connect_ipc()
    conn = ServerConnection(sock, loop)
    init_data = await conn.recv_init()
    return conn, init_data


async def connect_and_receive() -> Tuple[ServerState, List[int]]:
    """Legacy: connect and receive full state for backward compatibility."""
    if is_windows():
        return await _connect_and_receive_windows()

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.setblocking(True)
    sock.connect(socket_path())

    try:
        size_bytes = b""
        while len(size_bytes) < 4:
            chunk = sock.recv(4 - len(size_bytes))
            if not chunk:
                raise ConnectionError("Server closed connection")
            size_bytes += chunk
        expected_size = struct.unpack("!I", size_bytes)[0]

        raw_data, fds = recv_fds(sock, bufsize=max(65536, expected_size + 4096))
        state = deserialize_state(raw_data)

        for i, fd in enumerate(fds):
            if i < len(state.sessions):
                state.sessions[i].fd = fd
            try:
                os.fstat(fd)
            except OSError:
                pass

        for i, sh in enumerate(state.sessions):
            try:
                os.kill(sh.pid, 0)
            except OSError:
                pass

        return state, fds
    finally:
        sock.close()


async def _connect_and_receive_windows() -> Tuple[ServerState, List[int]]:
    port = read_port_file()
    if port is None:
        raise ConnectionError("No plmux server port found")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    sock.connect(("127.0.0.1", port))

    try:
        size_bytes = b""
        while len(size_bytes) < 4:
            chunk = sock.recv(4 - len(size_bytes))
            if not chunk:
                raise ConnectionError("Server closed connection")
            size_bytes += chunk
        expected_size = struct.unpack("!I", size_bytes)[0]

        raw_data = b""
        while len(raw_data) < expected_size:
            chunk = sock.recv(expected_size - len(raw_data))
            if not chunk:
                raise ConnectionError("Server closed connection")
            raw_data += chunk

        state = deserialize_state(raw_data)

        for i, sh in enumerate(state.sessions):
            sh.fd = sock.fileno()
            sh._sock = sock

        return state, [sock.fileno()]
    except Exception:
        sock.close()
        raise

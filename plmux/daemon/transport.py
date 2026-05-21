"""Daemon transport: fd passing, socket path helpers, platform detection."""

from __future__ import annotations

import array
import os
import socket
import sys
from pathlib import Path
from typing import List, Tuple

from plmux.config.loader import default_user_config_dir


def is_windows() -> bool:
    return sys.platform == "win32" or os.name == "nt"


def server_dir() -> Path:
    return default_user_config_dir()


def socket_path() -> str:
    return str(server_dir() / "plmux.sock")


def pid_path() -> str:
    return str(server_dir() / "plmux.pid")


def state_path() -> str:
    return str(server_dir() / "plmux_state.json")


def port_path() -> str:
    return str(server_dir() / "plmux.port")


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def write_port_file(port: int) -> None:
    server_dir().mkdir(parents=True, exist_ok=True)
    with open(port_path(), "w") as f:
        f.write(str(port))


def read_port_file() -> int | None:
    try:
        with open(port_path()) as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


def remove_port_file() -> None:
    try:
        os.unlink(port_path())
    except OSError:
        pass


def write_pid_file() -> None:
    server_dir().mkdir(parents=True, exist_ok=True)
    with open(pid_path(), "w") as f:
        f.write(str(os.getpid()))


def remove_pid_file() -> None:
    try:
        os.unlink(pid_path())
    except OSError:
        pass


def remove_socket_file() -> None:
    try:
        os.unlink(socket_path())
    except OSError:
        pass


def send_fds(sock: socket.socket, data_bytes: bytes, fds: List[int]) -> None:
    if is_windows():
        sock.sendall(data_bytes)
        return
    fds_array = array.array("i", fds)
    sock.sendmsg(
        [data_bytes],
        [(socket.SOL_SOCKET, socket.SCM_RIGHTS, fds_array)],
    )


def recv_fds(sock: socket.socket, bufsize: int = 65536) -> Tuple[bytes, List[int]]:
    if is_windows():
        data = b""
        while len(data) < bufsize:
            chunk = sock.recv(min(65536, bufsize - len(data)))
            if not chunk:
                break
            data += chunk
        return data, []
    msg, ancdata, _flags, _addr = sock.recvmsg(bufsize, socket.CMSG_SPACE(256))
    fds: List[int] = []
    for cmsg_level, cmsg_type, cmsg_data in ancdata:
        if cmsg_level == socket.SOL_SOCKET and cmsg_type == socket.SCM_RIGHTS:
            fds = list(array.array("i", cmsg_data))
    return msg, fds
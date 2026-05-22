"""Daemon server: run_server, client connection handling, PTY proxy."""

from __future__ import annotations

import asyncio
import os
import socket
import struct
from typing import Any, List

from plmux.daemon.state import ServerState, serialize_state
from plmux.daemon.transport import (
    is_windows,
    find_free_port,
    write_port_file,
    remove_port_file,
    write_pid_file,
    remove_pid_file,
    remove_socket_file,
    socket_path,
    send_fds,
)


async def _handle_client_connection(
    client: socket.socket,
    state: ServerState,
    loop: asyncio.AbstractEventLoop,
) -> None:
    try:
        fds = [s.fd for s in state.sessions]
        data = serialize_state(state)
        print(f"[DAEMON] sending state: len={len(data)}, sessions={len(state.sessions)}, fds={fds}", flush=True)
        for i, s in enumerate(state.sessions):
            print(f"[DAEMON] session[{i}]: index={s.index}, fd={s.fd}, pid={s.pid}, rows={s.rows}, cols={s.cols}", flush=True)
        await loop.sock_sendall(client, struct.pack("!I", len(data)))
        send_fds(client, data, fds)
        print("[DAEMON] state sent successfully", flush=True)
    except (BrokenPipeError, ConnectionResetError):
        pass
    finally:
        try:
            client.close()
        except OSError:
            pass


async def _handle_client_connection_windows(
    client: socket.socket,
    state: ServerState,
    procs: List[Any],
    loop: asyncio.AbstractEventLoop,
) -> None:
    try:
        data = serialize_state(state)
        await loop.sock_sendall(client, struct.pack("!I", len(data)))
        await loop.sock_sendall(client, data)

        await _proxy_pty_loop(client, procs, loop)
    except (BrokenPipeError, ConnectionResetError, asyncio.CancelledError):
        pass
    finally:
        try:
            client.close()
        except OSError:
            pass


async def _proxy_pty_loop(
    client: socket.socket,
    procs: List[Any],
    loop: asyncio.AbstractEventLoop,
) -> None:
    import queue
    import threading as _threading

    client.setblocking(False)

    header_buf = bytearray()

    async def _read_exact(n: int) -> bytes:
        nonlocal header_buf
        while len(header_buf) < n:
            try:
                chunk = await loop.sock_recv(client, max(4096, n - len(header_buf)))
            except (BlockingIOError, InterruptedError):
                await asyncio.sleep(0.001)
                continue
            if not chunk:
                raise ConnectionResetError("client disconnected")
            header_buf.extend(chunk)
        result = bytes(header_buf[:n])
        header_buf = header_buf[n:]
        return result

    async def _send_frame(session_id: int, cmd: int, payload: bytes) -> None:
        frame = struct.pack("!iBi", session_id, cmd, len(payload)) + payload
        try:
            await loop.sock_sendall(client, frame)
        except OSError:
            pass

    pty_queue: queue.Queue = queue.Queue()

    def _pty_reader_thread() -> None:
        while True:
            for si, p in enumerate(procs):
                if p is None:
                    continue
                try:
                    chunk = p.read(65536)
                    if chunk:
                        pty_queue.put((si, chunk))
                except (EOFError, OSError):
                    procs[si] = None
                except Exception:
                    pass
            import time
            time.sleep(0.01)

    _threading.Thread(target=_pty_reader_thread, name="plmux-daemon-pty-reader", daemon=True).start()

    async def _drain_pty_queue() -> None:
        while True:
            try:
                si, chunk = pty_queue.get_nowait()
                await _send_frame(si, 0x81, chunk)
            except queue.Empty:
                break

    try:
        while True:
            await _drain_pty_queue()

            try:
                header = await asyncio.wait_for(_read_exact(9), timeout=0.05)
            except asyncio.TimeoutError:
                continue

            session_id, cmd, payload_len = struct.unpack("!iBi", header)
            payload = b""
            if payload_len > 0:
                payload = await _read_exact(payload_len)

            if session_id < 0 or session_id >= len(procs) or procs[session_id] is None:
                continue

            p = procs[session_id]

            if cmd == 0x01:
                try:
                    p.write(payload)
                    flush = getattr(p, "flush", None)
                    if callable(flush):
                        flush()
                except OSError:
                    pass
            elif cmd == 0x02:
                if len(payload) >= 8:
                    rows, cols = struct.unpack("!ii", payload[:8])
                    try:
                        p.setwinsize(rows, cols)
                    except OSError:
                        pass
            elif cmd == 0x03:
                try:
                    p.close(force=True)
                except Exception:
                    pass
                procs[session_id] = None
            elif cmd == 0x04:
                alive = False
                try:
                    alive = p.isalive()
                except Exception:
                    pass
                await _send_frame(session_id, 0x82, b"\x01" if alive else b"\x00")
    finally:
        pass


async def run_server(state: ServerState) -> None:
    for i, sh in enumerate(state.sessions):
        try:
            os.fstat(sh.fd)
        except OSError:
            pass
        try:
            os.kill(sh.pid, 0)
        except OSError:
            pass

    server_dir = __import__("plmux.daemon.transport", fromlist=["server_dir"]).server_dir
    server_dir().mkdir(parents=True, exist_ok=True)
    loop = asyncio.get_running_loop()

    if is_windows():
        remove_port_file()
        port = find_free_port()
        write_port_file(port)
        write_pid_file()

        procs: List[Any] = [None] * len(state.sessions)
        for i, sh in enumerate(state.sessions):
            procs[i] = sh._proc if hasattr(sh, "_proc") else None

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", port))
        sock.listen(5)
        sock.setblocking(False)

        try:
            while True:
                client, _addr = await loop.sock_accept(sock)
                asyncio.ensure_future(
                    _handle_client_connection_windows(client, state, procs, loop)
                )
        except asyncio.CancelledError:
            pass
        finally:
            sock.close()
            remove_port_file()
            remove_pid_file()
        return

    remove_socket_file()
    write_pid_file()

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(socket_path())
    sock.listen(5)
    sock.setblocking(False)

    try:
        while True:
            client, _addr = await loop.sock_accept(sock)
            await _handle_client_connection(client, state, loop)
    except asyncio.CancelledError:
        pass
    finally:
        sock.close()
        remove_socket_file()
        remove_pid_file()
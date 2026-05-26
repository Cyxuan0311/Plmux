"""Daemon server: persistent process that holds PTY sessions and streams data to clients."""

from __future__ import annotations

import asyncio
import socket
from typing import Dict, List, Optional

from plmux.config.loader import load_config
from plmux.config.schema import PlmuxConfig
from plmux.daemon.state import ServerState
from plmux.daemon.transport import (
    is_windows,
    find_free_port,
    write_port_file,
    remove_port_file,
    write_pid_file,
    remove_pid_file,
    remove_socket_file,
    socket_path,
)
from plmux.ipc.server_conn import ClientConnection
from plmux.session.models import tree_to_json
from plmux.terminal.session import TerminalSession
from plmux.ui.theme import load_theme
from plmux.workspace import TmuxServer


class PlmuxDaemon:
    """Persistent daemon that owns the TmuxServer and manages client connections."""

    def __init__(self, ws: TmuxServer, cfg: PlmuxConfig) -> None:
        self.ws = ws
        self.cfg = cfg
        self.clients: List[ClientConnection] = []
        self._clients_lock = asyncio.Lock()
        self._pane_index_map: Dict[int, int] = {}
        self._index_pane_map: Dict[int, TerminalSession] = {}
        self._rebuild_pane_maps()
        self._pty_queue: asyncio.Queue = asyncio.Queue()
        self._running = True
        self._last_resize_rows: int = 0
        self._last_resize_cols: int = 0

    def _rebuild_pane_maps(self) -> None:
        self._pane_index_map.clear()
        self._index_pane_map.clear()
        global_idx = 0
        for sess in self.ws.sessions_list:
            for w in sess.windows:
                for s in w.panes:
                    self._pane_index_map[id(s)] = global_idx
                    self._index_pane_map[global_idx] = s
                    global_idx += 1

    def get_pane_index(self, session: TerminalSession) -> int:
        return self._pane_index_map.get(id(session), -1)

    def get_pane_by_index(self, idx: int) -> Optional[TerminalSession]:
        return self._index_pane_map.get(idx)

    def build_init_data(self) -> dict:
        sessions_data: list[dict] = []
        buffer_dumps: dict[str, str] = {}
        pane_info: list[dict] = []
        global_idx = 0

        for sess in self.ws.sessions_list:
            pane_offset = global_idx
            for w in sess.windows:
                for s in w.panes:
                    try:
                        buffer_dumps[str(global_idx)] = s.dump_buffer()
                    except Exception:
                        pass
                    pane_info.append({
                        "index": global_idx,
                        "pid": s.proc.pid if s.proc is not None else -1,
                        "argv": list(s.argv) if s.argv else [],
                        "rows": s.rows,
                        "cols": s.cols,
                    })
                    global_idx += 1
            windows_data = []
            for w in sess.windows:
                windows_data.append({
                    "tree": tree_to_json(w.tree),
                    "focus_pane": w.focus_pane,
                })
            sessions_data.append({
                "name": sess.name,
                "windows": windows_data,
                "current_window": sess.current_window,
                "pane_offset": pane_offset,
                "pane_count": global_idx - pane_offset,
            })

        cur_sess = self.ws._session()
        return {
            "tree": tree_to_json(cur_sess.tree),
            "focus_pane": cur_sess.focus_pane,
            "sessions_data": sessions_data,
            "current_session": self.ws.current_session,
            "buffer_dumps": buffer_dumps,
            "pane_count": global_idx,
            "pane_info": pane_info,
        }

    def build_state_update(self) -> dict:
        cur_sess = self.ws._session()
        sessions_data: list[dict] = []
        global_idx = 0
        for sess in self.ws.sessions_list:
            pane_offset = global_idx
            for w in sess.windows:
                for s in w.panes:
                    global_idx += 1
            windows_data = []
            for w in sess.windows:
                windows_data.append({
                    "tree": tree_to_json(w.tree),
                    "focus_pane": w.focus_pane,
                })
            sessions_data.append({
                "name": sess.name,
                "windows": windows_data,
                "current_window": sess.current_window,
                "pane_offset": pane_offset,
                "pane_count": global_idx - pane_offset,
            })
        return {
            "tree": tree_to_json(cur_sess.tree),
            "focus_pane": cur_sess.focus_pane,
            "sessions_data": sessions_data,
            "current_session": self.ws.current_session,
        }

    async def add_client(self, client: ClientConnection) -> None:
        init_data = self.build_init_data()
        await client.send_init(init_data)
        async with self._clients_lock:
            self.clients.append(client)

    async def remove_client(self, client: ClientConnection) -> None:
        async with self._clients_lock:
            if client in self.clients:
                self.clients.remove(client)
        client.close()

    async def broadcast_pane_output(self, pane_idx: int, data: bytes) -> None:
        async with self._clients_lock:
            dead = []
            for c in self.clients:
                if c.closed:
                    dead.append(c)
                    continue
                try:
                    await c.send_pane_output(pane_idx, data)
                except Exception:
                    dead.append(c)
            for c in dead:
                if c in self.clients:
                    self.clients.remove(c)
                c.close()

    async def broadcast_state_update(self) -> None:
        state_data = self.build_state_update()
        async with self._clients_lock:
            dead = []
            for c in self.clients:
                if c.closed:
                    dead.append(c)
                    continue
                try:
                    await c.send_state_update(state_data)
                except Exception:
                    dead.append(c)
            for c in dead:
                if c in self.clients:
                    self.clients.remove(c)
                c.close()

    async def broadcast_pane_closed(self, pane_idx: int) -> None:
        async with self._clients_lock:
            for c in self.clients:
                if not c.closed:
                    try:
                        await c.send_pane_closed(pane_idx)
                    except Exception:
                        pass

    def handle_client_key(self, pane_idx: int, data: bytes) -> None:
        pane = self.get_pane_by_index(pane_idx)
        if pane and not pane.closed:
            pane.write_bytes(data)

    def handle_client_resize(self, rows: int, cols: int) -> None:
        self._last_resize_rows = rows
        self._last_resize_cols = cols
        self.ws.sync_geometry(rows, cols)

    def handle_client_command(self, cmd: dict) -> None:
        action = cmd.get("action", "")
        need_rebuild = False
        need_sync_geometry = False
        if action == "split":
            direction = cmd.get("direction", "row")
            rows = cmd.get("rows", 0) or self._last_resize_rows or 24
            cols = cmd.get("cols", 0) or self._last_resize_cols or 80
            self.ws.sync_geometry(rows, cols)
            self.ws.split(direction)
            need_rebuild = True
            need_sync_geometry = True
        elif action == "only_pane":
            self.ws.only_pane()
            need_rebuild = True
            need_sync_geometry = True
        elif action == "new_window":
            self.ws.new_window()
            need_rebuild = True
            need_sync_geometry = True
        elif action == "close_window":
            self.ws.close_window()
            need_rebuild = True
            need_sync_geometry = True
        elif action == "next_window":
            self.ws.next_window()
        elif action == "prev_window":
            self.ws.prev_window()
        elif action == "goto_window":
            idx = cmd.get("index", 0)
            self.ws.goto_window(idx)
        elif action == "focus_prev":
            self.ws.focus_prev()
        elif action == "focus_next":
            self.ws.focus_next()
        elif action == "resize_pane":
            direction = cmd.get("direction", "left")
            self.ws.resize_pane(direction)
            need_sync_geometry = True
        elif action == "toggle_zoom":
            self.ws.toggle_zoom()
            need_sync_geometry = True
        elif action == "rotate_panes":
            direction = cmd.get("direction", "up")
            self.ws.rotate_panes(direction)
            need_sync_geometry = True
        elif action == "cycle_layout":
            self.ws.cycle_layout()
            need_sync_geometry = True
        elif action == "new_session":
            name = cmd.get("name", "")
            self.ws.new_session(name)
            need_rebuild = True
            need_sync_geometry = True
        elif action == "switch_session":
            idx = cmd.get("index", 0)
            self.ws.switch_session(idx)
            need_sync_geometry = True
        elif action == "kill_session":
            idx = cmd.get("index")
            if idx is not None:
                self.ws.kill_session(idx)
                need_rebuild = True
                need_sync_geometry = True
        elif action == "next_session":
            self.ws.next_session()
        elif action == "prev_session":
            self.ws.prev_session()
        elif action == "kill_pane":
            pane_idx = cmd.get("pane_index")
            if pane_idx is not None:
                self.ws.remove_pane(pane_idx)
                need_rebuild = True
                need_sync_geometry = True
        elif action == "focus_direction":
            direction = cmd.get("direction", "left")
            self.ws.focus_direction(direction)
        elif action == "swap_pane":
            direction = cmd.get("direction", "up")
            self.ws.swap_pane(direction)
            need_sync_geometry = True
        elif action == "break_pane":
            pane_idx = cmd.get("pane_index")
            self.ws.break_pane(pane_idx)
            need_rebuild = True
            need_sync_geometry = True
        elif action == "join_pane":
            direction = cmd.get("direction", "row")
            self.ws.join_pane(direction)
            need_rebuild = True
            need_sync_geometry = True
        elif action == "respawn_pane":
            pane_idx = cmd.get("pane_index")
            self.ws.respawn_pane(pane_idx)
            need_rebuild = True
            need_sync_geometry = True
        elif action == "send_keys":
            text = cmd.get("text", "")
            self.ws.send_keys(text)
        elif action == "rename_window":
            name = cmd.get("name", "")
            self.ws.rename_window(name)
        elif action == "rename_session":
            name = cmd.get("name", "")
            self.ws._session().name = name
            self.ws._mark()
        elif action == "set_focus_pane":
            idx = cmd.get("index", 0)
            self.ws.set_focus_pane(idx)
        elif action == "apply_layout_template":
            name = cmd.get("name", "")
            self.ws.apply_layout_template(name)
            need_rebuild = True
            need_sync_geometry = True
        elif action == "close_window_by_index":
            idx = cmd.get("index", 0)
            self.ws.close_window_by_index(idx)
            need_rebuild = True
            need_sync_geometry = True
        if need_rebuild:
            self._rebuild_pane_maps()
        if need_sync_geometry and self._last_resize_rows > 0 and self._last_resize_cols > 0:
            self.ws.sync_geometry(self._last_resize_rows, self._last_resize_cols)
        asyncio.ensure_future(self.broadcast_state_update())

    async def pump_pty_and_broadcast(self) -> None:
        while self._running:
            try:
                all_panes = self.ws.all_panes()

                for pane in all_panes:
                    if pane.closed:
                        continue
                    pane_idx = self.get_pane_index(pane)
                    if pane_idx < 0:
                        continue
                    need_snapshot = pane._scrollback_max > 0 and not pane.screen.use_alt_screen
                    snapshot = pane._snapshot_screen_rows() if need_snapshot else None
                    had_data = False
                    while True:
                        try:
                            data = pane._read_queue.get_nowait()
                            pane._detect_modes(data)
                            pane.stream.feed(data)
                            had_data = True
                            await self.broadcast_pane_output(pane_idx, data)
                        except Exception:
                            break
                    if had_data:
                        pane._capture_scrollback(snapshot)

                for si, sess in enumerate(self.ws.sessions_list):
                    for w in sess.windows:
                        dead = [i for i, s in enumerate(w.panes) if s.closed]
                        for di in sorted(dead, reverse=True):
                            pane_idx = self.get_pane_index(w.panes[di])
                            if pane_idx >= 0:
                                await self.broadcast_pane_closed(pane_idx)
                            if di < len(w.panes):
                                w.panes[di].close()
                                del w.panes[di]
                            self._rebuild_pane_maps()

                await asyncio.sleep(0.008)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(0.01)

    def shutdown(self) -> None:
        self._running = False
        for c in self.clients:
            c.close()
        self.ws.shutdown()


async def _handle_client(daemon: PlmuxDaemon, client_sock: socket.socket, loop: asyncio.AbstractEventLoop) -> None:
    client_sock.setblocking(False)
    conn = ClientConnection(
        client_sock,
        loop,
        on_key=daemon.handle_client_key,
        on_resize=daemon.handle_client_resize,
        on_command=daemon.handle_client_command,
        on_detach=lambda: asyncio.ensure_future(daemon.remove_client(conn)),
    )
    try:
        await daemon.add_client(conn)
        await conn.recv_loop()
    except (ConnectionResetError, BrokenPipeError, OSError):
        pass
    finally:
        await daemon.remove_client(conn)


async def run_daemon(daemon: PlmuxDaemon) -> None:
    loop = asyncio.get_running_loop()

    pump_task = asyncio.create_task(daemon.pump_pty_and_broadcast())

    server_dir = __import__("plmux.daemon.transport", fromlist=["server_dir"]).server_dir
    server_dir().mkdir(parents=True, exist_ok=True)

    if is_windows():
        remove_port_file()
        port = find_free_port()
        write_port_file(port)
        write_pid_file()

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", port))
        sock.listen(5)
        sock.setblocking(False)

        try:
            while daemon._running:
                client, _addr = await loop.sock_accept(sock)
                asyncio.ensure_future(_handle_client(daemon, client, loop))
        except asyncio.CancelledError:
            pass
        finally:
            sock.close()
            remove_port_file()
            remove_pid_file()
    else:
        remove_socket_file()
        write_pid_file()

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(socket_path())
        sock.listen(5)
        sock.setblocking(False)

        try:
            while daemon._running:
                client, _addr = await loop.sock_accept(sock)
                asyncio.ensure_future(_handle_client(daemon, client, loop))
        except asyncio.CancelledError:
            pass
        finally:
            sock.close()
            remove_socket_file()
            remove_pid_file()

    pump_task.cancel()
    try:
        await pump_task
    except asyncio.CancelledError:
        pass
    daemon.shutdown()


async def run_server(state: ServerState) -> None:
    """Legacy entry point: creates TmuxServer from ServerState and runs daemon."""
    cfg = load_config()
    theme = load_theme(cfg.theme)

    from plmux.state_bridge import build_workspace_from_state

    def dummy_dirty() -> None:
        pass

    ws = build_workspace_from_state(state, cfg, theme, dummy_dirty)

    daemon = PlmuxDaemon(ws, cfg)
    await run_daemon(daemon)


async def run_daemon_from_config(cfg: PlmuxConfig, *, restore=None) -> None:
    """New entry point: creates TmuxServer from config and runs daemon."""
    theme = load_theme(cfg.theme)

    def dummy_dirty() -> None:
        pass

    ws = TmuxServer(cfg, theme, on_dirty=dummy_dirty, restore=restore)

    daemon = PlmuxDaemon(ws, cfg)
    await run_daemon(daemon)

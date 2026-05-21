"""Application bootstrap: CLI parsing, config loading, and entry point."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from plmux import __version__
from plmux.config.loader import load_config
from plmux.config.schema import PlmuxConfig
from plmux.cli.commands import cmd_list_sessions, cmd_list_windows, cmd_kill_server
from plmux.daemon import is_server_alive, run_server, is_windows
from plmux.state_bridge import serve_mode, spawn_server_subprocess
from plmux.ui.theme import load_theme, Theme


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="plmux",
        description="Lightweight tmux-like PTY multiplexer",
        epilog=(
            "Examples:\n"
            "  plmux                  Start a new session\n"
            "  plmux ls               List active sessions\n"
            "  plmux attach           Attach to an existing session\n"
            "  plmux kill-server      Kill the running daemon\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="command", title="commands", metavar="COMMAND")

    sub.add_parser("ls", aliases=["list-sessions"], help="List active sessions")
    ls_p = sub.add_parser("lsw", aliases=["list-windows"], help="List windows")
    ls_p.add_argument("-p", "--panes", action="store_true", help="Also list panes in each window")
    attach_p = sub.add_parser("attach", aliases=["a"], help="Attach to an existing session")
    attach_p.add_argument("session", nargs="?", default=None, help="Pane index to focus (optional)")
    sub.add_parser("kill-server", help="Kill the running plmux daemon")
    sub.add_parser("new-session", help="Create a new detached plmux session")
    sub.add_parser("rename-window", help="Set a name for a window in saved session")
    sub.add_parser("swap-pane", help="Swap two pane indices in saved session")

    p.add_argument("--config", "-c", default=None, help="Path to config.json")
    p.add_argument("--debug", "-d", action="store_true", default=False, help="Enable debug logging to plmux_debug.log")
    p.add_argument("--version", "-v", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("--serve", default=None, help=argparse.SUPPRESS)
    return p


def run(argv: list[str] | None = None) -> None:
    from plmux.app.event_loop import async_main

    argv = argv if argv is not None else sys.argv[1:]
    p = build_arg_parser()
    ns = p.parse_args(argv)

    if ns.serve:
        serve_mode(ns.serve)
        return

    if ns.command in ("ls", "list-sessions"):
        cmd_list_sessions()
        return

    if ns.command in ("lsw", "list-windows"):
        cmd_list_windows(panes=getattr(ns, "panes", False))
        return

    if ns.command == "kill-server":
        cmd_kill_server()
        return

    try:
        import uvloop
        uvloop.install()
    except ImportError:
        pass

    attach_mode = ns.command in ("attach", "a") or (
        ns.command is None and is_server_alive()
    )
    target_session = getattr(ns, "session", None)

    try:
        detach_state = asyncio.run(async_main(ns.config, debug=ns.debug, attach_mode=attach_mode, target_session=target_session))
        if detach_state is not None:
            if attach_mode:
                kill_server()
            if hasattr(os, "fork"):
                pid = os.fork()
                if pid == 0:
                    os.setsid()
                    devnull = os.open(os.devnull, os.O_RDWR)
                    os.dup2(devnull, 0)
                    os.dup2(devnull, 1)
                    os.dup2(devnull, 2)
                    if devnull > 2:
                        os.close(devnull)
                    asyncio.run(run_server(detach_state))
                    os._exit(0)
            elif is_windows():
                spawn_server_subprocess(detach_state)
            else:
                asyncio.run(run_server(detach_state))
        elif attach_mode:
            from plmux.daemon import kill_server as _kill
            _kill()
    except KeyboardInterrupt:
        pass
    except (ConnectionRefusedError, FileNotFoundError, ConnectionError) as e:
        print(f"Error: Could not connect to plmux server: {e}", file=sys.stderr)
        sys.exit(1)
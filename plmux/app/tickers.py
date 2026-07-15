"""Background asyncio ticker coroutines for periodic tasks."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime

from plmux.extensions.registry import ExtensionContext, emit_hook
from plmux.modes import AppContext

_logger = logging.getLogger(__name__)


async def clock_ticker(ctx: AppContext) -> None:
    while ctx.running:
        await asyncio.sleep(1)
        new_time = datetime.now().strftime("%H:%M:%S")
        if new_time != ctx.clock_str:
            ctx.clock_str = new_time
            ctx.dirty = True


async def pet_ticker(ctx: AppContext) -> None:
    while ctx.running:
        await asyncio.sleep(0.8)
        if ctx.pet_mode_pane is not None:
            ctx.pet_frame += 1
            ctx.dirty = True


async def memory_ticker(ctx: AppContext) -> None:
    while ctx.running:
        await asyncio.sleep(2)
        if ctx.mode == "memory":
            ctx.dirty = True


async def status_refresh_ticker(ctx: AppContext) -> None:
    while ctx.running:
        await asyncio.sleep(2)
        try:
            pane_cwd = ""
            if ctx.ws and ctx.ws._window().panes:
                win = ctx.ws._window()
                fp = win.focus_pane
                if 0 <= fp < len(win.panes):
                    s = win.panes[fp]
                    if sys.platform != "win32" and os.name != "nt" and s.proc is not None:
                        try:
                            pane_cwd = os.readlink(f"/proc/{s.proc.pid}/cwd")
                        except OSError:
                            pass
                    if not pane_cwd:
                        try:
                            pane_cwd = os.getcwd()
                        except OSError:
                            pass
            await asyncio.to_thread(
                emit_hook,
                "status_refresh",
                ExtensionContext(hook_name="status_refresh", cwd=pane_cwd),
            )
            ctx.dirty = True
        except Exception:
            _logger.debug("status_refresh_ticker failed", exc_info=True)

"""Paste buffer manager (tmux-like buffer stack).

Provides a stack of named paste buffers that can be loaded from pane
selections, listed, pasted into panes, saved to / loaded from files,
and deleted.  The most-recently-added buffer is always on top.

API surface (mirrors tmux):
    BufferManager.get()          -> top buffer data or None
    BufferManager.set(data, name?) -> push a new buffer
    BufferManager.list()         -> [(name, size), ...]
    BufferManager.paste(name?)   -> data of named / top buffer
    BufferManager.delete(name)   -> remove by name
    BufferManager.save(name, path)  -> write to file
    BufferManager.load(path, name?) -> read from file
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PasteBuffer:
    name: str
    data: str
    created: float = field(default_factory=time.time)


class BufferManager:
    MAX_BUFFERS = 20

    def __init__(self) -> None:
        self._buffers: Dict[str, PasteBuffer] = {}
        self._stack: List[str] = []

    def set(self, data: str, name: Optional[str] = None) -> str:
        if name is None:
            name = f"buffer{len(self._stack)}"
        buf = PasteBuffer(name=name, data=data)
        if name in self._buffers:
            self._stack.remove(name)
        self._buffers[name] = buf
        self._stack.append(name)
        while len(self._stack) > self.MAX_BUFFERS:
            old = self._stack.pop(0)
            self._buffers.pop(old, None)
        return name

    def get(self) -> Optional[str]:
        if not self._stack:
            return None
        top = self._stack[-1]
        buf = self._buffers.get(top)
        return buf.data if buf else None

    def get_buffer(self, name: str) -> Optional[PasteBuffer]:
        return self._buffers.get(name)

    def paste(self, name: Optional[str] = None) -> Optional[str]:
        if name is not None:
            buf = self._buffers.get(name)
            return buf.data if buf else None
        return self.get()

    def list(self) -> List[tuple]:
        result = []
        for bname in reversed(self._stack):
            buf = self._buffers.get(bname)
            if buf:
                result.append((buf.name, len(buf.data), buf.created))
        return result

    def delete(self, name: str) -> bool:
        if name not in self._buffers:
            return False
        del self._buffers[name]
        self._stack.remove(name)
        return True

    def save(self, name: str, path: str) -> bool:
        buf = self._buffers.get(name)
        if buf is None:
            return False
        try:
            with open(path, "w", encoding="utf-8", errors="replace") as f:
                f.write(buf.data)
            return True
        except OSError:
            return False

    def load(self, path: str, name: Optional[str] = None) -> Optional[str]:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                data = f.read()
        except OSError:
            return None
        if name is None:
            base = os.path.basename(path)
            name = base
        return self.set(data, name)

    def clear(self) -> None:
        self._buffers.clear()
        self._stack.clear()

    @property
    def count(self) -> int:
        return len(self._stack)


_global_manager: Optional[BufferManager] = None


def get_buffer_manager() -> BufferManager:
    global _global_manager
    if _global_manager is None:
        _global_manager = BufferManager()
    return _global_manager

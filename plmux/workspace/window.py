from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from plmux.terminal.session import TerminalSession


@dataclass
class Window:
    tree: object = 0
    focus_pane: int = 0
    name: str = ""
    panes: List[TerminalSession] = field(default_factory=list)

    def pane(self, idx: int) -> Optional[TerminalSession]:
        if 0 <= idx < len(self.panes):
            return self.panes[idx]
        return None

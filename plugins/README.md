# plmux Plugins

This directory contains official plugins shipped with plmux. Each plugin lives in its own subdirectory with a `main.py` entry point.

## Directory Structure

```
plugins/
├── README.md
├── git-status/
│   └── main.py
└── battery-status/
    └── main.py
```

## Available Plugins

### git-status

Displays the current git branch and working tree status in the status bar.

**Status bar display:**

| State | Example | Color |
|-------|---------|-------|
| Clean | `main` | Green |
| Dirty (staged) | `feature +2` | Red |
| Dirty (modified) | `feature ~1` | Red |
| Dirty (untracked) | `feature ?3` | Red |
| Mixed | `develop +1 ~2 ?5` | Red |
| Not a git repo | _(hidden)_ | — |

**Indicators:**
- `+N` — N files staged (added, modified, renamed, or copied in index)
- `~N` — N files modified in working tree but not staged
- `?N` — N untracked files

**Performance:** Results are cached for 3 seconds and the `status_refresh` hook is throttled to once every 2 seconds, so this plugin adds negligible overhead.

### battery-status

Displays the current battery percentage and charging state in the status bar.

**Status bar display:**

| State | Example | Color |
|-------|---------|-------|
| Charging | `⚡85%` | Green |
| Full | `⚡100%` | Green |
| High (>60%) | `●72%` | Green |
| Medium (25-60%) | `◐45%` | Yellow |
| Low (<25%) | `○12%` | Red |
| No battery | _(hidden)_ | — |

**Platform support:** Linux (sysfs) and macOS (pmset).

**Performance:** Results are cached for 10 seconds since battery level changes slowly.

## Enabling Plugins

Add the plugin name to the `enabled` list in your config:

```json
{
  "extensions": {
    "enabled": ["git-status", "battery-status"],
    "search_paths": ["~/.config/plmux/extensions"]
  }
}
```

Copy the plugin directory (e.g. `git-status/`) to `~/.config/plmux/extensions/`, then add the plugin name to the `enabled` list.

## Writing Your Own Plugin

A plugin is a directory containing a `main.py` (or `__init__.py`) file. The file is executed on load and can register hooks, commands, key bindings, and status items.

### Quick Example

```python
# my-plugin/main.py
from plmux.extensions import register_hook, register_status_item, ExtensionContext

def on_status_refresh(ctx: ExtensionContext) -> None:
    register_status_item("my:hello", "bold white on #75715e")

register_hook("status_refresh", on_status_refresh)
```

### Available Hooks

| Hook | When |
|------|------|
| `app_started` | Application startup |
| `app_stopping` | Application shutdown |
| `pane_created` | New pane created |
| `pane_closed` | Pane removed |
| `pane_focus_changed` | Focus switched |
| `window_created` | New window created |
| `window_closed` | Window removed |
| `mode_changed` | Mode switched |
| `session_saved` | Session state saved |
| `session_loaded` | Session state loaded |
| `command_executed` | Command ran successfully |
| `command_unknown` | Unknown command entered |
| `status_refresh` | Status bar refresh (throttled ~2s) |

### API Reference

- `register_hook(name, fn)` — Register a hook handler
- `register_command(name, fn)` — Register a `:command`
- `register_key_binding(key, fn)` — Register a key binding
- `register_status_item(text, style)` — Add an item to the status bar

See the [Plugin System documentation](../docs/plugins.md) for the full API reference.

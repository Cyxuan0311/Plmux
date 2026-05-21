# Plugin System

plmux provides a tmux-like plugin extension system that allows you to hook into application lifecycle events, register custom commands, add key bindings, and extend the status bar.

## Configuration

Enable plugins in your `config.json`:

```json
{
  "extensions": {
    "enabled": ["my-plugin", "another-plugin"],
    "search_paths": ["~/.config/plmux/extensions"]
  }
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | `list[str]` | `[]` | Plugin names to load on startup |
| `search_paths` | `list[str]` | `["~/.config/plmux/extensions"]` | Directories to search for plugins |

## Plugin Discovery

When a plugin name is listed in `enabled`, plmux searches for it in the following order:

1. **Python package**: `plmux_extensions.<name>` (installable via pip)
2. **Directory with `__init__.py`**: `<search_path>/<name>/__init__.py`
3. **Directory with `main.py`**: `<search_path>/<name>/main.py`
4. **Single file**: `<search_path>/<name>.py`

The first match found is loaded. If no match is found, a warning is logged and startup continues.

## Plugin Structure

A plugin is simply a Python module that calls registration functions at import time. No special class or decorator is required.

### Single-File Plugin

```
~/.config/plmux/extensions/
└── hello.py
```

```python
from plmux.extensions import register_hook, register_command, ExtensionContext

def on_start(ctx: ExtensionContext) -> None:
    print("Hello from hello plugin!")

register_hook("app_started", on_start)
```

### Directory Plugin

```
~/.config/plmux/extensions/
└── my-plugin/
    ├── __init__.py
    └── helpers.py
```

`__init__.py`:

```python
from plmux.extensions import register_hook, register_command, ExtensionContext
from .helpers import greet

def on_start(ctx: ExtensionContext) -> None:
    greet("my-plugin loaded")

def cmd_greet(ws, args) -> None:
    from plmux.input.commands import CommandResult
    name = args[0] if args else "world"
    return CommandResult(f"Hello, {name}!")

register_hook("app_started", on_start)
register_command("greet", cmd_greet)
```

## Hook Reference

Hooks are callback functions that receive an `ExtensionContext` and are called when specific events occur.

### ExtensionContext Fields

| Field | Type | Description |
|-------|------|-------------|
| `hook_name` | `str` | Name of the hook that triggered this callback |
| `extra_config` | `dict` | Unknown top-level keys from `config.json` |
| `pane_index` | `int` | Affected pane index (`-1` if not applicable) |
| `window_index` | `int` | Affected window index (`-1` if not applicable) |
| `mode` | `str` | Current mode string (e.g. `"NORMAL"`, `"PREFIX"`) |
| `command` | `str` | Command name for command-related hooks |
| `message` | `str` | Additional context message |

### Available Hooks

| Hook | Triggered When | Context Fields |
|------|---------------|----------------|
| `app_started` | Application has finished initializing | `extra_config` |
| `app_stopping` | Application is about to exit | `extra_config` |
| `pane_created` | A new pane is created | `pane_index` |
| `pane_closed` | A pane is closed | `pane_index` |
| `pane_focus_changed` | Focus moves to a different pane | `pane_index`, `message` (previous pane index) |
| `window_created` | A new window is created | `window_index`, `pane_index` |
| `window_closed` | A window is closed | `window_index` |
| `mode_changed` | Input mode changes | `mode` |
| `session_saved` | Session state is saved to disk | — |
| `session_loaded` | Session state is restored from disk | — |
| `command_executed` | A `:` command is executed | `command` |
| `command_unknown` | An unrecognized command is entered | `command` |
| `status_refresh` | Status bar is about to refresh | — |

### Registering Hooks

```python
from plmux.extensions import register_hook, ExtensionContext

def on_pane_created(ctx: ExtensionContext) -> None:
    print(f"Pane {ctx.pane_index} created")

register_hook("pane_created", on_pane_created)
```

Multiple hooks can be registered for the same event. They are called in registration order. If a hook raises an exception, it is logged and remaining hooks continue to execute.

## Plugin API

### register_command(name, fn)

Register a custom `:` command.

The handler signature is `fn(ws: PaneWorkspace, args: list[str]) -> CommandResult`.

```python
from plmux.extensions import register_command
from plmux.input.commands import CommandResult

def cmd_echo(ws, args) -> CommandResult:
    return CommandResult(" ".join(args) if args else "")

register_command("echo", cmd_echo)
```

After loading this plugin, users can type `:echo hello world` in the command line.

### register_key_binding(key, fn)

Register a key binding handler.

The handler signature is `fn(ws: PaneWorkspace) -> None`.

```python
from plmux.extensions import register_key_binding

def toggle_feature(ws) -> None:
    pass

register_key_binding("ctrl+g", toggle_feature)
```

### register_status_item(name, style)

Add a custom item to the status bar.

```python
from plmux.extensions import register_status_item

register_status_item("git-branch", "bold magenta on default")
```

### register_hook(name, fn)

Register a callback for a hook event (see Hook Reference above).

## Comparison with tmux Plugins

| Feature | tmux | plmux |
|---------|------|-------|
| Hook events | `@plugin` + TPM | `register_hook()` |
| Custom commands | `run-shell` | `register_command()` |
| Key bindings | `bind-key` | `register_key_binding()` |
| Status line items | `#{...}` format | `register_status_item()` |
| Plugin manager | TPM (3rd party) | Built-in `extensions.enabled` |
| Search paths | `TMUX_PLUGIN_MANAGER_PATH` | `extensions.search_paths` |
| Auto-loading | TPM `@plugin` list | `extensions.enabled` list |

## Example Plugins

### Git Branch in Status Bar

```python
# ~/.config/plmux/extensions/git-branch.py
import subprocess
from plmux.extensions import register_hook, register_status_item, ExtensionContext

def refresh_git(ctx: ExtensionContext) -> None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=1,
        )
        branch = result.stdout.strip()
        if branch:
            register_status_item(f"git:{branch}", "bold magenta on default")
    except Exception:
        pass

register_hook("status_refresh", refresh_git)
```

### Session Save Notification

```python
# ~/.config/plmux/extensions/notify.py
from plmux.extensions import register_hook, ExtensionContext

def on_save(ctx: ExtensionContext) -> None:
    print("\a")  # terminal bell

def on_load(ctx: ExtensionContext) -> None:
    print("Session restored.")

register_hook("session_saved", on_save)
register_hook("session_loaded", on_load)
```

### Custom Command with Auto-Completion

```python
# ~/.config/plmux/extensions/project.py
from plmux.extensions import register_command
from plmux.input.commands import CommandResult

PROJECTS = {"work": "~/work", "personal": "~/projects"}

def cmd_project(ws, args) -> CommandResult:
    if not args:
        return CommandResult("Usage: :project <name>")
    name = args[0]
    path = PROJECTS.get(name)
    if not path:
        return CommandResult(f"Unknown project: {name}")
    for session in ws.sessions:
        session.write(f"cd {path}\n".encode())
    return CommandResult(f"Switched to {name}")

register_command("project", cmd_project)
```

Implementation: [registry.py](../plmux/extensions/registry.py)

# Configuration

Configuration is stored in JSON format. plmux loads settings from two sources and deep-merges them:

1. **Package defaults**: [defaults.json](../plmux/config/defaults.json)
2. **User config**: auto-created on first run

## User Config Location

| Platform | Path |
|----------|------|
| Linux / macOS | `~/.config/plmux/config.json` (respects `$XDG_CONFIG_HOME`) |
| Windows | `%APPDATA%\plmux\config.json` (or `%LOCALAPPDATA%`) |

Implementation: [loader.py](../plmux/config/loader.py#L24-L28)

## Default Settings

```json
{
  "shell": null,
  "env": {},
  "ui": {
    "refresh_hz": 60,
    "use_alternate_screen": true,
    "status_position": "bottom",
    "command_line_height": 1,
    "min_pane_rows": 3,
    "min_pane_cols": 10
  },
  "keys": {
    "prefix": "ctrl+b",
    "command_line": ":",
    "bindings": {
      "split-vertical": ["%", "v"],
      "split-horizontal": ["\"", "s"],
      "only-pane": ["o"],
      "next-window": ["n"],
      "prev-window": ["p"],
      "new-window": ["c"],
      "close-window": ["&"],
      "copy-mode": ["["],
      "cycle-layout": [" "],
      "help": ["?"],
      "detach": ["d"],
      "focus-left": ["h"],
      "focus-right": ["l"],
      "focus-up": ["k"],
      "focus-down": ["j"],
      "resize-left": ["H"],
      "resize-right": ["L"],
      "resize-up": ["K"],
      "resize-down": ["J"],
      "zoom": ["z"],
      "command-line": [":"]
    }
  },
  "session": {
    "auto_save": true,
    "state_path": null
  },
  "theme": "default",
  "extensions": {
    "enabled": [],
    "search_paths": ["~/.config/plmux/extensions"]
  },
  "hooks": {}
}
```

## Field Reference

### Top-Level Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `shell` | `list[str] \| null` | `null` | Shell command and arguments; defaults to system shell when `null` |
| `env` | `dict[str, str]` | `{}` | Extra environment variables passed to child shells (inherited by all sessions) |
| `theme` | `string` | `"default"` | Active theme name; see [Themes](themes.md) |
| `ui` | object | — | UI rendering options (see below) |
| `keys` | object | — | Key binding options (see below) |
| `session` | object | — | Session persistence options (see below) |
| `extensions` | object | — | Extension options (see below) |
| `hooks` | object | — | Hook command options (see below) |

Unknown top-level keys are preserved in `PlmuxConfig.extra` for experimentation.

Implementation: [schema.py](../plmux/config/schema.py)

### `ui` — UI Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `refresh_hz` | `float` | `60` | Screen refresh rate in Hz |
| `use_alternate_screen` | `bool` | `true` | Use alternate screen buffer |
| `status_position` | `string` | `"bottom"` | Status bar position: `"top"` or `"bottom"` |
| `command_line_height` | `int` | `1` | Height of the command-line bar in rows |
| `min_pane_rows` | `int` | `3` | Minimum rows a pane can shrink to |
| `min_pane_cols` | `int` | `10` | Minimum columns a pane can shrink to |

### `keys` — Key Binding Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `prefix` | `string` | `"ctrl+b"` | Prefix key chord for all key bindings |
| `command_line` | `string` | `":"` | Character that triggers command-line mode |
| `bindings` | `dict[str, list[str]]` | (see defaults) | Action-to-key mapping; see [Key Bindings](keybindings.md) for full details |

#### `keys.bindings` — Action Key Mapping

Each key in `bindings` maps an action name to a list of key strings. The first matching key triggers the action. You can add multiple keys for the same action, or remove keys by omitting them from the list.

| Action | Default Keys | Description |
|--------|-------------|-------------|
| `split-vertical` | `["%", "v"]` | Split pane side-by-side |
| `split-horizontal` | `["\"", "s"]` | Split pane stacked |
| `only-pane` | `["o"]` | Keep only current pane |
| `next-window` | `["n"]` | Switch to next window |
| `prev-window` | `["p"]` | Switch to previous window |
| `new-window` | `["c"]` | Create a new window |
| `close-window` | `["&"]` | Close current window |
| `copy-mode` | `["["]` | Enter copy mode |
| `cycle-layout` | `[" "]` | Cycle layout templates |
| `help` | `["?"]` | Show help overlay |
| `detach` | `["d"]` | Detach from session |
| `focus-left` | `["h"]` | Focus previous pane |
| `focus-right` | `["l"]` | Focus next pane |
| `focus-up` | `["k"]` | Focus previous pane |
| `focus-down` | `["j"]` | Focus next pane |
| `resize-left` | `["H"]` | Resize pane left |
| `resize-right` | `["L"]` | Resize pane right |
| `resize-up` | `["K"]` | Resize pane up |
| `resize-down` | `["J"]` | Resize pane down |
| `zoom` | `["z"]` | Toggle pane zoom |
| `command-line` | `[":"]` | Enter command-line mode |

For the full key binding reference including copy mode, command mode, and overlay modes, see [Key Bindings](keybindings.md).

### `session` — Session Persistence Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `auto_save` | `bool` | `true` | Automatically save session layout on exit |
| `state_path` | `string \| null` | `null` | Custom path for session state file; defaults to user config dir when `null` |

### `extensions` — Extension Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | `list[str]` | `[]` | List of extension names to load |
| `search_paths` | `list[str]` | `["~/.config/plmux/extensions"]` | Directories to search for extensions |

### `hooks` — Hook Commands

Hook commands are shell commands that run automatically when specific events occur. Each key is a hook name and the value is a list of shell commands to execute.

```json
{
  "hooks": {
    "pane_created": ["echo 'New pane created'"],
    "app_started": ["notify-send 'plmux started'"],
    "session_saved": ["echo 'Session saved' >> /tmp/plmux.log"]
  }
}
```

| Hook | Triggered When |
|------|---------------|
| `app_started` | Application has finished initializing |
| `app_stopping` | Application is about to exit |
| `pane_created` | A new pane is created |
| `pane_closed` | A pane is closed |
| `pane_focus_changed` | Focus moves to a different pane |
| `window_created` | A new window is created |
| `window_closed` | A window is closed |
| `mode_changed` | Input mode changes |
| `session_saved` | Session state is saved to disk |
| `session_loaded` | Session state is restored from disk |
| `session_created` | A new session is created |
| `session_killed` | A session is killed |
| `command_executed` | A `:` command is executed |
| `command_unknown` | An unrecognized command is entered |
| `status_refresh` | Status bar is about to refresh |
| `client_connected` | A client connects to the server |
| `client_disconnected` | A client disconnects from the server |
| `pane_resized` | A pane is resized |

When a hook command runs, the following environment variables are set:

| Variable | Description |
|----------|-------------|
| `PLMUX_HOOK_NAME` | Name of the hook that triggered |
| `PLMUX_PANE_INDEX` | Affected pane index (if applicable) |
| `PLMUX_SESSION_INDEX` | Affected session index (if applicable) |
| `PLMUX_CWD` | Current working directory (if available) |

Hook commands run asynchronously in the background and do not block the main event loop.

Implementation: [registry.py](../plmux/extensions/registry.py)

### Environment Variable Inheritance

Environment variables follow an inheritance chain: **Server → Session → Pane**.

1. The top-level `env` field in `config.json` sets the base environment for all sessions
2. Each session inherits a copy of the server's environment at creation time
3. Session-specific variables can be set at runtime via the `:setenv` command
4. New panes within a session inherit the session's current environment

```
config.json env  →  Session.env  →  Pane (spawned with merged env)
                       ↑
                 :setenv FOO bar  (adds/overrides at session level)
```

This means changes to a session's environment only affect panes created after the change, not existing panes.

## Hot Reload

plmux supports hot-reloading configuration changes without restarting:

### Automatic File Watch

plmux watches the user config file for changes. When the file is modified on disk, the configuration is automatically reloaded:

- **Theme changes** are applied immediately
- **Key binding changes** take effect on the next key press
- **Newly enabled plugins** are loaded automatically
- **UI settings** (refresh rate, status position, etc.) are applied on the next frame

### Manual Reload

Use the `:reload` or `:source` command to manually trigger a configuration reload:

```
:reload
:source
```

This is useful when the file watcher misses a change (e.g., on network filesystems).

### What Gets Reloaded

| Setting | Hot-Reloadable | Notes |
|---------|---------------|-------|
| `theme` | Yes | Applied immediately |
| `keys.prefix` | Yes | Takes effect on next prefix press |
| `keys.command_line` | Yes | Takes effect on next command mode entry |
| `keys.bindings` | Yes | Takes effect on next key press |
| `ui.refresh_hz` | Yes | Applied on next frame |
| `ui.status_position` | Yes | Applied on next frame |
| `ui.*` (other) | Yes | Applied on next frame |
| `extensions.enabled` | Partial | New plugins are loaded; removed plugins stay loaded until restart |
| `shell` | No | Only affects new panes/windows |
| `env` | No | Only affects new panes/windows |
| `session.*` | No | Session settings require restart |

Implementation: [event_loop.py](../plmux/app/event_loop.py) (`_ConfigWatcher`) | [cmdline.py](../plmux/modes/cmdline.py) (`_do_reload_config`)

## Loading Process

1. Package defaults are loaded from `plmux/config/defaults.json`
2. If the user config file does not exist, it is created from defaults
3. User config is deep-merged on top of defaults (nested dicts are merged recursively)
4. The result is parsed into a typed `PlmuxConfig` dataclass

Implementation: [loader.py](../plmux/config/loader.py#L30-L38)

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
    "command_line": ":"
  },
  "session": {
    "auto_save": true,
    "state_path": null
  },
  "theme": "default",
  "extensions": {
    "enabled": [],
    "search_paths": ["~/.config/plmux/extensions"]
  }
}
```

## Field Reference

### Top-Level Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `shell` | `list[str] \| null` | `null` | Shell command and arguments; defaults to system shell when `null` |
| `env` | `dict[str, str]` | `{}` | Extra environment variables passed to child shells |
| `theme` | `string` | `"default"` | Active theme name; see [Themes](themes.md) |
| `ui` | object | — | UI rendering options (see below) |
| `keys` | object | — | Key binding options (see below) |
| `session` | object | — | Session persistence options (see below) |
| `extensions` | object | — | Extension options (see below) |

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

## Loading Process

1. Package defaults are loaded from `plmux/config/defaults.json`
2. If the user config file does not exist, it is created from defaults
3. User config is deep-merged on top of defaults (nested dicts are merged recursively)
4. The result is parsed into a typed `PlmuxConfig` dataclass

Implementation: [loader.py](../plmux/config/loader.py#L30-L38)

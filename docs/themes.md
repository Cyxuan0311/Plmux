# Themes

Themes are JSON data that control the visual appearance of plmux. They define colors and styles for the status bar, pane borders, pane titles, command line, and mode indicators.

## Selecting a Theme

Set the `theme` field in your [configuration](configuration.md):

```json
{
  "theme": "default"
}
```

Or change it at runtime with the `:theme` command:

```
:theme dracula
```

## Built-in Themes

plmux ships with the following built-in themes:

| Theme | Description |
|-------|-------------|
| `default` | Green-tinted status bar with dark pane borders |
| `dracula` | Purple accents on dark background |
| `gruvbox` | Warm yellow/orange tones |
| `monokai` | Classic green-on-dark editor palette |
| `nord` | Cool blue-grey Scandinavian palette |
| `solarized` | Teal/cyan based on the Solarized specification |
| `tokyonight` | Blue/purple night-city palette |
| `catppuccin` | Soft lavender/pastel palette |
| `ayu` | Warm golden accents on dark background |
| `material` | Purple/pink accents inspired by Material Design |
| `one-dark` | Purple/cyan accents from the One Dark theme |
| `rose-pine` | Soft purple/gold natural palette |
| `everforest` | Muted pink/green forest palette |
| `kanagawa` | Purple/blue Japanese-inspired palette |
| `cyberpunk` | Neon pink/green futuristic palette |
| `oceanic-next` | Purple/teal ocean palette |
| `base16` | Muted purple/green base16 palette |
| `alabaster` | Clean light theme with soft grey tones |
| `apprentice` | Low-contrast dark theme for extended coding |
| `horizon` | Bold pink/red accents on deep dark background |
| `papercolor` | Light theme inspired by PaperColor Vim |
| `vscode-dark` | Blue status bar inspired by VS Code dark theme |
| `green-screen` | Phosphor green monochrome retro terminal |

Implementation: [theme.py](../plmux/ui/theme.py#L56-L537)

## Theme Fields

A theme JSON object contains the following sections:

### `name`

Display name of the theme.

### `mode` — Mode Indicator Styles

| Field | Purpose |
|-------|---------|
| `mode.normal` | Style for the normal-mode indicator |
| `mode.prefix` | Style for the prefix-mode indicator |
| `mode.cmdline` | Style for the command-line-mode indicator |

### `status` — Status Bar Styles

| Field | Purpose |
|-------|---------|
| `status.style` | Status bar brand segment style |
| `status.muted` | Status bar secondary text style |
| `status.background` | Status bar background color |
| `status.win` | Window segment style |
| `status.pane` | Pane segment style |
| `status.clock` | Clock segment style |
| `status.host` | Host segment style |
| `status.command` | Foreground command segment style |

### `pane` — Pane Styles

| Field | Purpose |
|-------|---------|
| `pane.active_border` | Focused pane border color |
| `pane.inactive_border` | Unfocused pane border color |
| `pane.title_active` | Active pane title style |
| `pane.title_inactive` | Inactive pane title style |

### `cmdline` — Command Line Styles

| Field | Purpose |
|-------|---------|
| `cmdline.indicator` | Command indicator style |
| `cmdline.body` | Command input style |
| `cmdline.background` | Command line background color |
| `cmdline.indicator_fg` | Command indicator foreground color |

### Custom Keys

Unknown keys are preserved in `Theme.extra` for experimentation. This allows you to add custom fields without breaking the theme loader.

Implementation: [theme.py `_parse_theme_data`](../plmux/ui/theme.py#L540-L567)

## User-Defined Themes

User themes are loaded from a `themes.json` file in the user config directory:

| Platform | Path |
|----------|------|
| Linux / macOS | `~/.config/plmux/themes.json` |
| Windows | `%APPDATA%\plmux\themes.json` |

The file should contain a JSON object where each key is a theme name and the value follows the theme field structure above. User themes override built-in themes with the same name.

Example `themes.json`:

```json
{
  "my-theme": {
    "name": "my-theme",
    "mode": {
      "normal": "bold black on #ff0000",
      "prefix": "bold black on #00ff00",
      "cmdline": "bold black on #0000ff"
    },
    "status": {
      "style": "bold white on #ff0000",
      "muted": "dim white on #ff0000",
      "background": "#ff0000",
      "win": "bold white on #00ff00",
      "pane": "dim white on #333333",
      "clock": "dim white on #ff0000",
      "host": "bold white on #ff0000"
    },
    "pane": {
      "active_border": "#ff0000",
      "inactive_border": "#333333",
      "title_active": "bold white on #333333",
      "title_inactive": "grey62 on #1a1a1a"
    },
    "cmdline": {
      "indicator": "bold #ff0000 on #2d2d2d",
      "body": "bold #ffffff on #2d2d2d",
      "background": "#2d2d2d",
      "indicator_fg": "#ff0000"
    }
  }
}
```

## Style Syntax

Styles use Rich's style syntax. Common patterns:

| Syntax | Meaning |
|--------|---------|
| `bold` | Bold text |
| `dim` | Dim/faint text |
| `white` | Named foreground color |
| `on #hex` | Background color in hex |
| `bold white on #333` | Combined: bold white text on dark grey background |

Implementation: [theme.py](../plmux/ui/theme.py)

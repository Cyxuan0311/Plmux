<div align="center">
  <img 
    src="resource/logo.png" 
    alt="plmux logo" 
    width="120" 
    style="border-radius: 16px; overflow: hidden;"
  />

# plmux ： Python Lightweight Terminal Multiplexer

[中文文档](README.zh-CN.md) | English

[![Version](https://img.shields.io/badge/version-0.1.0-blueviolet.svg)](https://github.com/Frames/plmux/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-0078D4.svg)](https://github.com/Frames/plmux)
</div>



A lightweight, cross-platform terminal multiplexer inspired by tmux, built with Python, Rich, and C extensions. It provides pane splitting, window management, mouse support (scroll, click-to-focus, drag-to-resize), copy mode, a vim-style command interface, dynamic status bar with foreground process display, 36 built-in themes, session persistence, a browser-based web client, a tmux-like plugin extension system, and hot-reloadable configuration.

<div align="center">
  <img src="resource/demo.png" alt="plmux demo" />
  <p>plmux operation in windows terminal(wsl2)</p>
</div>

## Features

- **Pane Splitting**: Vertical and horizontal splits with adjustable ratios
- **Window Management**: Multiple windows with layout cycling
- **Mouse Support**: Scroll wheel to scroll pane content, click to switch focus, drag borders to resize panes; automatically forwards mouse events to child programs (e.g. vim, less)
- **Zoom**: Toggle any pane to fullscreen and back
- **Layout Templates**: 10 built-in layout templates (even-horizontal, main-vertical, quad, columns, etc.)
- **Copy Mode**: Text selection and clipboard integration
- **Command Line**: Vim-style `:` command interface with tab completion
- **Dynamic Status Bar**: Real-time display of mode, window, pane, foreground command (nano, btop, fzf, etc.), clock, and hostname
- **Themes**: 36 built-in themes (dracula, gruvbox, tokyonight, catppuccin, nord, edge, doom-one, challenger-deep, moonlight, forest-night, snazzy, and more) + user-defined JSON themes
- **Hot Reload**: Configuration and plugin changes are automatically detected and applied without restart
- **Web Client**: Browser-based terminal access via WebSocket with C extension acceleration
- **Plugin System**: tmux-like extension hooks, custom commands, key bindings, and status items
- **C Extensions**: FastScreen (ANSI parsing/rendering) and WebSocket kernel for high-performance frame processing
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Session Persistence**: Auto-save and restore layouts
- **Daemon Mode**: Detach and reattach sessions in the background

## Quick Start

### Installation

```bash
pip install .
```

Or install in development mode:

```bash
pip install -e .
```

### Usage

```bash
plmux                  # Start a new session
plmux ls               # List active sessions
plmux lsw              # List windows
plmux lsw -p           # List windows with pane details
plmux attach           # Attach to an existing session
plmux new-session      # Create a detached session
plmux kill-server      # Kill the running daemon
```

## Key Bindings

### Prefix

All key bindings are prefixed by **Ctrl+B** (configurable). See [Key Bindings](docs/keybindings.md) for full documentation.

| Action | Binding |
|--------|---------|
| Prefix | `Ctrl+B` |
| Vertical split | Prefix + `%` or `v` |
| Horizontal split | Prefix + `"` or `s` |
| Focus with hjkl | Prefix + `h` `j` `k` `l` |
| Focus with arrows | Prefix + `←` `↓` `↑` `→` |
| Only this pane | Prefix + `o` |
| Zoom pane | Prefix + `z` |
| New window | Prefix + `c` |
| Next/prev window | Prefix + `n` / `p` |
| Goto window 0-9 | Prefix + `0`-`9` |
| Cycle layout | Prefix + `Space` |
| Enter copy mode | Prefix + `[` |
| Resize pane | Prefix + `H` `J` `K` `L` |
| Show help | Prefix + `?` |
| Detach session | Prefix + `d` |
| Close window | Prefix + `&` |
| Force quit | `Ctrl+Q` |

### Mouse Operations

| Action | Description |
|--------|-------------|
| Scroll wheel up/down | Scroll pane content (scrollback buffer) |
| Left click on pane | Switch focus to that pane |
| Left click on border | Begin pane resize drag |
| Drag on border | Resize adjacent panes |
| Mouse events in child programs | Automatically forwarded when child enables mouse mode |

### Copy Mode

See [Copy Mode](docs/copy_mode.en.md) for full documentation.

### Command Line

Press `Esc` then `:` to enter command mode.

| Command | Description |
|---------|-------------|
| `:exit` | Hard quit (clear all saved state) |
| `:split`, `:sp` | Horizontal split |
| `:vsplit`, `:vsp`, `:vs` | Vertical split |
| `:only` | Keep only current pane |
| `:focus <n>` | Focus pane by index |
| `:theme <name>` | Change theme |
| `:theme list` | Open theme browser |
| `:layout` | Open layout browser |
| `:layout <name>` | Apply named layout template |
| `:web [port]` | Start web client (default port 9888) |
| `:webstop` | Stop web client server |
| `:ls` | Open session browser |
| `:plugins` | Open plugin manager |
| `:reload`, `:source` | Reload configuration and load newly enabled plugins |
| `:help` | Show help overlay |

Use `Tab` for command completion.

## Hot Reload

plmux automatically watches the configuration file for changes. When you edit `config.json`, changes are applied immediately:

- **Theme changes** take effect instantly
- **Key binding changes** apply on the next key press
- **Newly enabled plugins** are loaded automatically
- **UI settings** apply on the next frame

You can also manually trigger a reload with `:reload` or `:source`.

See [Configuration - Hot Reload](docs/configuration.md#hot-reload) for details on what can and cannot be hot-reloaded.

## Web Client (Planned)

plmux includes a built-in web server that allows browser-based terminal access. See [Web Client](docs/web-client.md) for full documentation.

```bash
:web              # Start on default port 9888
:web 8080         # Start on custom port
:webstop          # Stop the server
```

Then open `http://localhost:9888` in your browser.

## Configuration

See [Configuration](docs/configuration.md) for full documentation. Key binding customization is documented in [Key Bindings](docs/keybindings.md).

## Themes

See [Themes](docs/themes.md) for full documentation.

## Plugins

See [Plugins](docs/plugins.md) for full documentation.

## Architecture

plmux uses C extensions for performance-critical paths and a modular architecture for maintainability:

- **FastScreen** (`plmux/terminal/_c_extension/`): ANSI parsing, screen state management, and rendering — falls back to a pure-Python pyte backend when unavailable
- **WebSocket Kernel** (`plmux/web/_c_extension/`): Frame parsing and encoding for browser terminal — falls back to pure-Python WebSocket when unavailable
- **Mouse Handler** (`plmux/app/mouse_handler.py`): Decoupled mouse event processing — scroll, click-to-focus, drag-to-resize, and child program mouse forwarding
- **Terminal Session** (`plmux/terminal/session.py`): PTY-backed terminal with public API for scroll offset, copy mode state, and scrollback buffer management

Both C extensions are optional; plmux works without them using Python fallbacks.

## License

MIT

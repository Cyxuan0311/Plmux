# Web Client

plmux includes a built-in web server that provides browser-based terminal access via WebSocket. This allows you to interact with your plmux sessions from any device with a web browser.

## Starting the Web Server

From within plmux, use the `:web` command:

```
:web              # Start on default port 9888
:web 8080         # Start on custom port
```

To stop the server:

```
:webstop
```

Then open `http://localhost:9888` (or your custom port) in a browser.

## Features

- **Full Terminal Emulation**: xterm.js-based rendering with ANSI color support
- **Keyboard Input**: All standard keys, Ctrl combinations, Alt combinations, function keys, and arrow keys
- **Dynamic Resize**: Terminal automatically resizes to fit the browser window
- **Theme Sync**: The web client reflects the current plmux theme colors
- **Status Bar**: Real-time display of mode, window, pane, and foreground command
- **Paste Support**: Paste text from clipboard via the browser
- **TLS/HTTPS**: Encrypted remote access via configurable SSL/TLS certificates
- **Token Authentication**: Secure access with read-write and read-only tokens
- **Session Routing**: Direct access to specific sessions via URL paths (e.g., `/session/my-session`)
- **Read-Only Mode**: Share sessions for observation without allowing input

## Keyboard Support

The web client maps browser keyboard events to terminal escape sequences:

| Browser Key | Terminal Sequence |
|-------------|-------------------|
| `Enter` | `\r` (carriage return) |
| `Backspace` | `\x7f` (DEL) |
| `Tab` | `\t` |
| `Escape` | `\x1b` |
| `Arrow Up/Down/Left/Right` | `\x1b[A/B/C/D` |
| `Home` / `End` | `\x1b[H` / `\x1b[F` |
| `Delete` / `Insert` | `\x1b[3~` / `\x1b[2~` |
| `PageUp` / `PageDown` | `\x1b[5~` / `\x1b[6~` |
| `F1`–`F12` | `\x1b[11~` / `\x1b[12~` / ... |
| `Ctrl+A`–`Ctrl+Z` | `\x01`–`\x1a` |
| `Ctrl+[` / `Ctrl+]` / `Ctrl+\` | `\x1b` / `\x1d` / `\x1c` |
| `Alt+<key>` | `\x1b<key>` |

Implementation: [web/__init__.py](../plmux/web/__init__.py) — `_web_key_to_terminal()`

## Remote Access

plmux supports secure remote access to your terminal sessions from a browser or another terminal.

### TLS/HTTPS

To enable HTTPS, configure the TLS certificate and key in your config file:

```json
{
  "web": {
    "host": "0.0.0.0",
    "port": 9888,
    "tls_cert": "/path/to/cert.pem",
    "tls_key": "/path/to/key.pem"
  }
}
```

When TLS is configured, the web server automatically uses HTTPS and the WebSocket connection upgrades to `wss://`. The minimum TLS version is 1.2.

### Token Authentication

Enable token-based authentication to restrict access:

```json
{
  "web": {
    "auth_enabled": true,
    "tokens": ["my-secret-rw-token"],
    "readonly_tokens": ["observer-token"]
  }
}
```

- **Read-write tokens** (`tokens`): Full terminal access including input
- **Read-only tokens** (`readonly_tokens`): View-only access — all keyboard input, paste, and resize actions are blocked

Tokens can be provided via:
- URL query parameter: `https://server:9888/?token=my-secret-rw-token`
- HTTP header: `Authorization: Bearer my-secret-rw-token`

### Token Management Panel

Use the `:web-token` command to open an interactive overlay panel for managing tokens:

```
:web-token
```

| Key | Action |
|-----|--------|
| `g` | Generate a read-write token |
| `r` | Generate a read-only token |
| `d` | Revoke the selected token |
| `y` | Copy the last generated token to clipboard |
| `↑` / `k` | Move cursor up |
| `↓` / `j` | Move cursor down |
| `Home` | Jump to top |
| `G` | Jump to bottom |
| `Esc` / `q` | Close panel |

The panel displays all active tokens with their prefix, hash, and mode (read-write or read-only). Newly generated tokens are shown at the bottom of the panel and can be copied with `y`.

### Session Routing

Access a specific session directly via URL path:

```
https://server:9888/session/my-session?token=xxx
```

This opens the web client focused on the named session.

### Status Indicators

The web client status bar shows security indicators:

- **🔒 TLS** — Shown when connected via HTTPS (green badge)
- **🔒 READ-ONLY** — Shown when authenticated with a read-only token (red badge)

## Architecture

### WebSocket Communication

The web server uses a custom WebSocket implementation (no external dependencies):

1. **HTTP Server**: Built on `asyncio.start_server` — serves the HTML page on `GET /` and upgrades to WebSocket on `GET /ws`
2. **Frame Parser**: Parses incoming WebSocket frames from the browser client
3. **Frame Encoder**: Encodes outgoing messages as WebSocket text frames

### C Extension Acceleration

When the C extension (`_ws_kernel`) is available, WebSocket frame parsing and encoding are handled in C for improved performance:

- `FrameParser`: Incremental frame parser with `feed()` + `parse()` API
- `encode_text_frame()`: Encode text data into WebSocket frames
- `encode_binary_frame()`: Encode binary data into WebSocket frames
- `encode_close_frame()`: Encode close frames
- `encode_pong_frame()`: Encode pong responses

When the C extension is not available, a pure-Python fallback is used automatically.

Implementation: [web/_c_extension/](../plmux/web/_c_extension/)

### Message Protocol

The web client communicates using JSON messages over WebSocket:

**Client → Server:**

| Type | Fields | Description |
|------|--------|-------------|
| `key` | `key`, `ctrl`, `alt`, `shift`, `code` | Keyboard event |
| `input` | `data` | Raw text input |
| `paste` | `text` | Pasted text |
| `ready` | `cols`, `rows` | Client initialized with terminal size |
| `resize` | `cols`, `rows` | Browser window resized |
| `focus` | `idx` | Focus changed to pane `idx` |
| `resize_pane` | `idx`, `rows` | Resize pane `idx` to `rows` |

**Server → Client:**

| Type | Fields | Description |
|------|--------|-------------|
| `output` | `data` | Terminal output (ANSI text) |
| `snapshot` | `data` | Initial screen content on connection |
| `status` | `mode`, `win`, `pane`, `cmd`, `clock`, `host` | Status bar update |
| `theme` | `name`, `mode`, `status`, `pane`, `cmdline` | Theme color data |
| `layout` | `tree`, `focus`, `panes` | Layout structure update |
| `mode` | `mode`, `prev_mode` | Mode change notification |
| `overlay` | `kind`, `content` | Overlay panel display |
| `overlay_close` | | Close overlay panel |

### Output Pipeline

Terminal output from PTY sessions is piped to web clients through an efficient pipeline:

1. PTY output is captured via an output hook on each `TerminalSession.stream`
2. Output chunks are enqueued into an `asyncio.Queue`
3. A drain loop batches chunks (33ms interval) and broadcasts to all connected clients
4. When the C extension is available, frames are encoded directly in C

Implementation: [web/server.py](../plmux/web/server.py) — `_broadcast_loop()`

## Security Considerations

- The web server binds to `0.0.0.0` by default, making it accessible from any network interface
- For local-only access, set `"host": "127.0.0.1"` in the web config or ensure your firewall blocks external access to port 9888
- **Token authentication** is available — enable `auth_enabled` in the web config and configure `tokens` and `readonly_tokens`
- **TLS/HTTPS** is supported — configure `tls_cert` and `tls_key` to encrypt all traffic
- Without authentication enabled, anyone who can reach the port has full terminal access
- Read-only tokens allow sharing sessions for observation without granting input capability
- Tokens are stored as SHA-256 hashes — plaintext tokens are only shown once at generation time

## Limitations

- Mouse events are not forwarded to the terminal (mouse-dependent TUI apps may not work)
- Scrollback buffer is limited to the current screen content
- Multiple browser clients share the same terminal sessions (no multiplexing)

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

**Server → Client:**

| Type | Fields | Description |
|------|--------|-------------|
| `output` | `data` | Terminal output (ANSI text) |
| `snapshot` | `data` | Initial screen content on connection |
| `status` | `mode`, `win`, `pane`, `cmd`, `clock`, `host` | Status bar update |
| `theme` | `name`, `mode`, `status`, `pane`, `cmdline` | Theme color data |

### Output Pipeline

Terminal output from PTY sessions is piped to web clients through an efficient pipeline:

1. PTY output is captured via an output hook on each `TerminalSession.stream`
2. Output chunks are enqueued into an `asyncio.Queue`
3. A drain loop batches chunks (33ms interval) and broadcasts to all connected clients
4. When the C extension is available, frames are encoded directly in C

Implementation: [web/server.py](../plmux/web/server.py) — `_broadcast_loop()`

## Security Considerations

- The web server binds to `0.0.0.0` by default, making it accessible from any network interface
- For local-only access, start with `:web` and ensure your firewall blocks external access to port 9888
- There is **no authentication** — anyone who can reach the port has full terminal access
- Use with caution on shared or public networks

## Limitations

- Mouse events are not forwarded to the terminal (mouse-dependent TUI apps may not work)
- Scrollback buffer is limited to the current screen content
- Multiple browser clients share the same terminal sessions (no multiplexing)

# Key Bindings

All key bindings in plmux are prefixed by a **prefix key** (default: `Ctrl+B`). Press the prefix key first, then press the action key.

## Prefix Key

The default prefix is `Ctrl+B`. You can change it in `config.json`:

```json
{
  "keys": {
    "prefix": "ctrl+a"
  }
}
```

Supported prefix values: `ctrl+b`, `ctrl+a`, `c-b`, `c-a`, `^b`, `^a`.

Pressing the prefix key twice (e.g. `Ctrl+B` `Ctrl+B`) sends the prefix key itself to the child program.

Implementation: [schema.py](../plmux/config/schema.py) | [prefix.py](../plmux/modes/prefix.py)

## Pane Management

| Action | Default Binding | Description |
|--------|----------------|-------------|
| Vertical split | `%` or `v` | Split the current pane side-by-side |
| Horizontal split | `"` or `s` | Split the current pane stacked |
| Only this pane | `o` | Close all other panes, keep only the current one |
| Zoom pane | `z` | Toggle the current pane to fullscreen and back |
| Kill pane | `x` | Close the current pane (close window if last pane) |
| Swap pane up | `{` | Swap current pane with the one above |
| Swap pane down | `}` | Swap current pane with the one below |
| Break pane | `!` | Break the current pane out into its own window |
| Focus left | `h` | Move focus to the left pane (spatial direction) |
| Focus right | `l` | Move focus to the right pane (spatial direction) |
| Focus up | `k` | Move focus to the pane above (spatial direction) |
| Focus down | `j` | Move focus to the pane below (spatial direction) |
| Focus (arrow keys) | `←` `→` `↑` `↓` | Move focus with arrow keys (spatial direction) |
| Resize left | `H` | Shrink the pane from the left edge |
| Resize right | `L` | Expand the pane to the right |
| Resize up | `K` | Shrink the pane from the top edge |
| Resize down | `J` | Expand the pane downward |

## Window Management

| Action | Default Binding | Description |
|--------|----------------|-------------|
| New window | `c` | Create a new window |
| Next window | `n` | Switch to the next window |
| Previous window | `p` | Switch to the previous window |
| Goto window 0-9 | `0`–`9` | Switch to window by index |
| Close window | `&` | Close the current window (quit if last) |
| Cycle layout | `Space` | Cycle through available layout templates |

## Mode Switching

| Action | Default Binding | Description |
|--------|----------------|-------------|
| Enter copy mode | `[` | Enter text selection mode |
| Show help | `?` | Open the help overlay |
| Detach session | `d` | Detach from the session (session continues in background) |
| Enter command line | `:` | Open the `:` command prompt |
| Send prefix key | Prefix+Prefix | Send the prefix key to the child program |

## Direct Keys (No Prefix)

| Key | Action |
|-----|--------|
| `Ctrl+Q` | Force quit plmux |
| `Esc` | Passed through directly to the child program (e.g. vim exit insert mode) |

## Mouse Operations

plmux supports mouse interaction via SGR mouse protocol (DEC mode 1006). Mouse events are automatically enabled on startup.

Implementation: [mouse_handler.py](../plmux/app/mouse_handler.py)

| Action | Description |
|--------|-------------|
| Scroll wheel up | Scroll pane content up (scrollback buffer) |
| Scroll wheel down | Scroll pane content down |
| Left click on pane | Switch focus to the clicked pane |
| Left click on border | Begin pane resize drag |
| Drag on border | Resize adjacent panes proportionally |
| Mouse events in child programs | Automatically forwarded when the child program enables mouse mode (e.g. vim mouse mode, less scrolling) |

When a child program (such as vim with `set mouse=a`) enables mouse mode, plmux detects this and forwards all mouse events directly to that program instead of handling them itself.

## Copy Mode

Copy mode uses vim-like key bindings for text navigation and selection.

Implementation: [copy_mode.py](../plmux/modes/copy_mode.py)

| Key | Action |
|-----|--------|
| `h` / `←` | Move cursor left |
| `j` / `↓` | Move cursor down |
| `k` / `↑` | Move cursor up |
| `l` / `→` | Move cursor right |
| `w` | Move forward one word |
| `b` | Move backward one word |
| `0` / `Home` | Move to start of line |
| `$` / `End` | Move to end of line |
| `g` | Move to first line |
| `G` | Move to last line |
| `Ctrl+u` | Scroll up half page |
| `Ctrl+d` | Scroll down half page |
| `Space` | Start / toggle selection |
| `Enter` | Copy selection to clipboard and exit copy mode |
| `v` | Toggle character/line selection mode |
| `Esc` / `q` | Exit copy mode |

## Command Line Mode

Press `Prefix` then `:` to enter command mode. Use `Tab` for auto-completion, `↑` `↓` to browse command history.

Implementation: [commands.py](../plmux/input/commands.py)

| Command | Description |
|---------|-------------|
| `:exit` | Hard quit (clear all saved state) |
| `:split`, `:sp` | Horizontal split |
| `:vsplit`, `:vsp`, `:vs` | Vertical split |
| `:only` | Keep only current pane |
| `:focus <n>` | Focus pane by index |
| `:kill-pane [n]`, `:killp` | Kill pane (close window if last pane) |
| `:swap-pane [up\|down]`, `:swapp` | Swap current pane with neighbor |
| `:break-pane`, `:breakp` | Break pane into its own window |
| `:join-pane [h\|v]`, `:joinp` | Join pane from next window |
| `:respawn-pane [n]`, `:respawnp` | Respawn dead pane (restart shell) |
| `:send-keys <text>`, `:sendk` | Send text to active pane |
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

## Dead Panes

When a process inside a pane exits and `remain_on_exit` is enabled, the pane is preserved with a `[PROCESS EXITED]` indicator. You can then:

- Press `Prefix+x` to kill the pane
- Type `:respawn-pane` to restart the shell in the pane

Enable in `config.json`:

```json
{
  "ui": {
    "remain_on_exit": true
  }
}
```

## Theme List Mode

| Key | Action |
|-----|--------|
| `↑` / `k` | Move cursor up |
| `↓` / `j` | Move cursor down |
| `Home` / `g` | Jump to first theme |
| `End` / `G` | Jump to last theme |
| `PageUp` | Scroll up 5 themes |
| `PageDown` | Scroll down 5 themes |
| `Enter` | Apply selected theme |
| `Esc` / `q` | Cancel and return |

## Plugin List Mode

| Key | Action |
|-----|--------|
| `↑` / `k` | Move cursor up |
| `↓` / `j` | Move cursor down |
| `Home` / `g` | Jump to first plugin |
| `End` / `G` | Jump to last plugin |
| `PageUp` | Scroll up 5 plugins |
| `PageDown` | Scroll down 5 plugins |
| `Space` | Toggle enable/disable plugin |
| `Esc` / `q` | Close and return |

## Session List Mode

| Key | Action |
|-----|--------|
| `↑` / `k` | Move cursor up |
| `↓` / `j` | Move cursor down |
| `Enter` | Attach to selected session |
| `Esc` / `q` | Cancel and return |

## Layout List Mode

| Key | Action |
|-----|--------|
| `↑` / `k` | Move cursor up |
| `↓` / `j` | Move cursor down |
| `Enter` | Apply selected layout |
| `Esc` / `q` | Cancel and return |

## Customizing Key Bindings

Key bindings can be customized in `config.json` under `keys.bindings`:

```json
{
  "keys": {
    "prefix": "ctrl+b",
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
      "kill-pane": ["x"],
      "swap-pane-up": ["{"],
      "swap-pane-down": ["}"],
      "break-pane": ["!"],
      "command-line": [":"]
    }
  }
}
```

Each action maps to a list of keys. The first matching key triggers the action. You can add multiple keys for the same action, or remove keys by omitting them from the list.

### Available Binding Actions

| Action | Description |
|--------|-------------|
| `split-vertical` | Split pane side-by-side |
| `split-horizontal` | Split pane stacked |
| `only-pane` | Keep only current pane |
| `next-window` | Switch to next window |
| `prev-window` | Switch to previous window |
| `new-window` | Create a new window |
| `close-window` | Close current window |
| `copy-mode` | Enter copy mode |
| `cycle-layout` | Cycle layout templates |
| `help` | Show help overlay |
| `detach` | Detach from session |
| `focus-left` | Focus left pane (spatial direction) |
| `focus-right` | Focus right pane (spatial direction) |
| `focus-up` | Focus pane above (spatial direction) |
| `focus-down` | Focus pane below (spatial direction) |
| `resize-left` | Resize pane left |
| `resize-right` | Resize pane right |
| `resize-up` | Resize pane up |
| `resize-down` | Resize pane down |
| `zoom` | Toggle pane zoom |
| `kill-pane` | Kill current pane |
| `swap-pane-up` | Swap with pane above |
| `swap-pane-down` | Swap with pane below |
| `break-pane` | Break pane into its own window |
| `command-line` | Enter command-line mode |

Implementation: [schema.py](../plmux/config/schema.py) | [prefix.py](../plmux/modes/prefix.py)

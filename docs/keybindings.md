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

Implementation: [schema.py](../plmux/config/schema.py) | [prefix.py](../plmux/modes/prefix.py)

## Pane Management

| Action | Default Binding | Description |
|--------|----------------|-------------|
| Vertical split | `%` or `v` | Split the current pane side-by-side |
| Horizontal split | `"` or `s` | Split the current pane stacked |
| Only this pane | `o` | Close all other panes, keep only the current one |
| Zoom pane | `z` | Toggle the current pane to fullscreen and back |
| Focus left | `h` | Move focus to the previous pane |
| Focus right | `l` | Move focus to the next pane |
| Focus up | `k` | Move focus to the previous pane |
| Focus down | `j` | Move focus to the next pane |
| Focus (arrow keys) | `←` `→` `↑` `↓` | Move focus with arrow keys |
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
| Enter command line | `Esc` then `:` | Open the `:` command prompt |

## Direct Keys (No Prefix)

| Key | Action |
|-----|--------|
| `Ctrl+Q` | Force quit plmux |
| `Esc` | Enter escape-wait state; if followed by `:`, enters command mode |

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

Press `Esc` then `:` to enter command mode. Use `Tab` for auto-completion.

Implementation: [commands.py](../plmux/input/commands.py)

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
      "zoom": ["z"]
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
| `focus-left` | Focus previous pane |
| `focus-right` | Focus next pane |
| `focus-up` | Focus previous pane |
| `focus-down` | Focus next pane |
| `resize-left` | Resize pane left |
| `resize-right` | Resize pane right |
| `resize-up` | Resize pane up |
| `resize-down` | Resize pane down |
| `zoom` | Toggle pane zoom |

Implementation: [schema.py](../plmux/config/schema.py) | [prefix.py](../plmux/modes/prefix.py)

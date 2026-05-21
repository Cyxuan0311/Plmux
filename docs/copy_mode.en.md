# Copy Mode — Interactive Text Selection

Copy mode allows you to select and copy text content from the terminal.

## Key Bindings

| Key | Action |
|-----|--------|
| `Prefix + [` | Enter copy mode |
| `Esc` or `q` | Exit copy mode |
| Arrow keys | Move selection cursor |
| `PageUp` | Page up (move by visible pane height) |
| `PageDown` | Page down (move by visible pane height) |
| `Home` | Move to start of current line |
| `End` | Move to end of current line |
| `V` | Toggle line selection mode |
| `y` | Yank (copy) selection to clipboard and exit |
| Mouse click+drag | Select text by dragging (auto-enters copy mode) |

## Selection Modes

- **Character selection** (default): Select text character by character
- **Line selection**: Toggle with `V`; selects entire lines

## Mouse Support

Clicking and dragging in a pane automatically enters copy mode and creates a selection. The selection anchor is set at the click position, and the cursor follows the drag. Releasing the mouse button ends the drag but stays in copy mode — press `y` to yank or `Esc`/`q` to exit.

## Implementation Details

### Selection Representation

- Selections are represented as `(row, col)` half-open intervals
- Cross-line selection is supported
- Reverse selection is supported (start point can come after end point)

### Rendering

- Selected text is highlighted with the `reverse` style
- Selection boundaries are stored in the session's `_copy_sel_start` and `_copy_sel_end` attributes

### Clipboard Integration

When copying, the following priority is used:

1. `pyperclip` (primary method)
2. Platform fallbacks:
   - macOS: `pbcopy`
   - Windows: `clip`
   - Linux: `xclip`

Implementation: [clipboard.py](../plmux/platform/clipboard.py)

## Notes

- In environments without X11 (e.g., pure SSH sessions), clipboard fallbacks may not work
- Copy operations are best-effort; success is not guaranteed in all environments

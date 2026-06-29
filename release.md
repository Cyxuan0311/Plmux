# Release Notes

## v0.1.0 — Initial Release

### Core Features
- Multi-window/pane tmux session management
- Command-line mode (`:` shortcut) with tab completion
- Command alias support
- Plugin system (load, unload, configure)
- Config auto-reload
- Mouse event support (select, resize, scroll)
- Copy mode (scrollback search, select, copy)
- Format variable substitution engine (`{session_name}`, `{window_name}`, `{pane_index}`, etc.)
- Buffer manager
- Hook system (`on_pre_exec`, `on_post_exec`, `on_pane_focus`, etc.)
- IPC support (daemon mode)

### User Interface
- Memory usage overlay (`:memory`) — tree view with processes, sessions, windows, panes; gradient progress bars
- Clock overlay (adapts to pane width)
- Pet / RPG stats panel (HP/ATK/DEF/SPD/INT)
- File browser plugin (icons, directory expansion, scrolling)
- Web token management overlay
- Pane & status bar style configuration screens
- Status bar gradient display
- Rounded border / box theme support

### Web Client
- Built-in Web server for remote access
- JWT authentication
- Read-only mode
- Session routing and management
- Pane resizing, terminal font optimization
- New connection UI and overlay handling

### Themes
- 20+ built-in themes (`ayu`, `nord`, `dracula`, `solarized`, etc.)
- Hot-switch themes (`:theme <name>`)

### Engineering & Dev
- Event loop decomposed into 6 focused modules
- Mouse handler extracted into dedicated module
- Workspace / pane / session abstraction layer
- Windows / Linux / macOS compatibility handling
- CI workflow (GitHub Actions)
- pytest test suite

### Fixes
- Fixed circular import issues
- Fixed test mock coverage
- Fixed Windows spawn flag compatibility
- Cleaned up unused imports and dead code

### Documentation
- Bilingual docs (EN/ZH): configuration, keybindings, themes, plugins, Web client
- Mouse operation guide
- Copy mode usage

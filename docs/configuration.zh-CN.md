# 配置

配置以 JSON 格式存储。plmux 从两个来源加载设置并进行深度合并：

1. **包默认值**：[defaults.json](../plmux/config/defaults.json)
2. **用户配置**：首次运行时自动创建

## 用户配置路径

| 平台 | 路径 |
|------|------|
| Linux / macOS | `~/.config/plmux/config.json`（遵循 `$XDG_CONFIG_HOME`） |
| Windows | `%APPDATA%\plmux\config.json`（或 `%LOCALAPPDATA%`） |

实现：[loader.py](../plmux/config/loader.py#L24-L28)

## 默认配置

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

## 字段说明

### 顶层字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `shell` | `list[str] \| null` | `null` | Shell 命令及参数；为 `null` 时使用系统默认 shell |
| `env` | `dict[str, str]` | `{}` | 传递给子 shell 的额外环境变量（所有会话继承） |
| `theme` | `string` | `"default"` | 当前主题名称；参见[主题](themes.zh-CN.md) |
| `ui` | object | — | UI 渲染选项（见下文） |
| `keys` | object | — | 键绑定选项（见下文） |
| `session` | object | — | 会话持久化选项（见下文） |
| `extensions` | object | — | 扩展选项（见下文） |
| `hooks` | object | — | 钩子命令选项（见下文） |

未识别的顶层键会保留在 `PlmuxConfig.extra` 中，便于试验新功能。

实现：[schema.py](../plmux/config/schema.py)

### `ui` — UI 选项

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `refresh_hz` | `float` | `60` | 屏幕刷新率（Hz） |
| `use_alternate_screen` | `bool` | `true` | 使用备用屏幕缓冲区 |
| `status_position` | `string` | `"bottom"` | 状态栏位置：`"top"` 或 `"bottom"` |
| `command_line_height` | `int` | `1` | 命令行栏高度（行数） |
| `min_pane_rows` | `int` | `3` | 窗格最小行数 |
| `min_pane_cols` | `int` | `10` | 窗格最小列数 |

### `keys` — 键绑定选项

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `prefix` | `string` | `"ctrl+b"` | 所有快捷键的前缀键 |
| `command_line` | `string` | `":"` | 触发命令行模式的字符 |
| `bindings` | `dict[str, list[str]]` | （见默认值） | 操作到按键的映射；详见[快捷键](keybindings.zh-CN.md) |

#### `keys.bindings` — 操作按键映射

`bindings` 中的每个键将操作名称映射到按键字符串列表。第一个匹配的按键触发操作。可以为同一操作添加多个按键，也可以通过从列表中移除按键来删除绑定。

| 操作 | 默认按键 | 说明 |
|------|----------|------|
| `split-vertical` | `["%", "v"]` | 左右分割窗格 |
| `split-horizontal` | `["\"", "s"]` | 上下分割窗格 |
| `only-pane` | `["o"]` | 仅保留当前窗格 |
| `next-window` | `["n"]` | 切换到下一个窗口 |
| `prev-window` | `["p"]` | 切换到上一个窗口 |
| `new-window` | `["c"]` | 创建新窗口 |
| `close-window` | `["&"]` | 关闭当前窗口 |
| `copy-mode` | `["["]` | 进入复制模式 |
| `cycle-layout` | `[" "]` | 循环布局模板 |
| `help` | `["?"]` | 显示帮助覆盖层 |
| `detach` | `["d"]` | 分离会话 |
| `focus-left` | `["h"]` | 焦点移至上一个窗格 |
| `focus-right` | `["l"]` | 焦点移至下一个窗格 |
| `focus-up` | `["k"]` | 焦点移至上一个窗格 |
| `focus-down` | `["j"]` | 焦点移至下一个窗格 |
| `resize-left` | `["H"]` | 向左调整窗格大小 |
| `resize-right` | `["L"]` | 向右调整窗格大小 |
| `resize-up` | `["K"]` | 向上调整窗格大小 |
| `resize-down` | `["J"]` | 向下调整窗格大小 |
| `zoom` | `["z"]` | 切换窗格缩放 |
| `command-line` | `[":"]` | 进入命令行模式 |

完整的快捷键参考（包括复制模式、命令模式和覆盖层模式），请参见[快捷键](keybindings.zh-CN.md)。

### `session` — 会话持久化选项

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `auto_save` | `bool` | `true` | 退出时自动保存会话布局 |
| `state_path` | `string \| null` | `null` | 会话状态文件的自定义路径；为 `null` 时使用用户配置目录 |

### `extensions` — 扩展选项

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enabled` | `list[str]` | `[]` | 要加载的扩展名称列表 |
| `search_paths` | `list[str]` | `["~/.config/plmux/extensions"]` | 搜索扩展的目录列表 |

### `hooks` — 钩子命令

钩子命令是在特定事件发生时自动运行的 Shell 命令。每个键是钩子名称，值是要执行的 Shell 命令列表。

```json
{
  "hooks": {
    "pane_created": ["echo '新窗格已创建'"],
    "app_started": ["notify-send 'plmux 已启动'"],
    "session_saved": ["echo '会话已保存' >> /tmp/plmux.log"]
  }
}
```

| 钩子 | 触发时机 |
|------|---------|
| `app_started` | 应用完成初始化 |
| `app_stopping` | 应用即将退出 |
| `pane_created` | 新窗格创建 |
| `pane_closed` | 窗格关闭 |
| `pane_focus_changed` | 焦点切换到其他窗格 |
| `window_created` | 新窗口创建 |
| `window_closed` | 窗口关闭 |
| `mode_changed` | 输入模式变更 |
| `session_saved` | 会话状态保存到磁盘 |
| `session_loaded` | 会话状态从磁盘恢复 |
| `session_created` | 新会话创建 |
| `session_killed` | 会话被杀死 |
| `command_executed` | 执行 `:` 命令 |
| `command_unknown` | 输入未识别的命令 |
| `status_refresh` | 状态栏即将刷新 |
| `client_connected` | 客户端连接到服务器 |
| `client_disconnected` | 客户端断开与服务器的连接 |
| `pane_resized` | 窗格大小调整 |

钩子命令运行时，会设置以下环境变量：

| 变量 | 说明 |
|------|------|
| `PLMUX_HOOK_NAME` | 触发的钩子名称 |
| `PLMUX_PANE_INDEX` | 受影响的窗格索引（如适用） |
| `PLMUX_SESSION_INDEX` | 受影响的会话索引（如适用） |
| `PLMUX_CWD` | 当前工作目录（如可用） |

钩子命令在后台异步运行，不会阻塞主事件循环。

实现：[registry.py](../plmux/extensions/registry.py)

### 环境变量继承

环境变量遵循继承链：**Server → Session → Pane**。

1. `config.json` 中的顶层 `env` 字段设置所有会话的基础环境
2. 每个会话在创建时继承服务器环境的副本
3. 会话级别的变量可以在运行时通过 `:setenv` 命令设置
4. 会话内的新窗格继承该会话的当前环境

```
config.json env  →  Session.env  →  Pane（使用合并后的环境生成）
                       ↑
                  :setenv FOO bar  （在会话级别添加/覆盖）
```

这意味着对会话环境的更改仅影响更改后创建的窗格，不影响已有窗格。

## 热更新

plmux 支持无需重启即可热更新配置：

### 自动文件监听

plmux 监视用户配置文件的变化。当文件在磁盘上被修改时，配置会自动重新加载：

- **主题更改**立即生效
- **快捷键更改**在下次按键时生效
- **新启用的插件**自动加载
- **UI 设置**（刷新率、状态栏位置等）在下一帧生效

### 手动重载

使用 `:reload` 或 `:source` 命令手动触发配置重载：

```
:reload
:source
```

当文件监听器遗漏了变更时（例如在网络文件系统上），这很有用。

### 可热更新的设置

| 设置 | 可热更新 | 说明 |
|------|----------|------|
| `theme` | 是 | 立即生效 |
| `keys.prefix` | 是 | 下次按前缀键时生效 |
| `keys.command_line` | 是 | 下次进入命令模式时生效 |
| `keys.bindings` | 是 | 下次按键时生效 |
| `ui.refresh_hz` | 是 | 下一帧生效 |
| `ui.status_position` | 是 | 下一帧生效 |
| `ui.*`（其他） | 是 | 下一帧生效 |
| `extensions.enabled` | 部分 | 新插件会加载；已移除的插件在重启前仍保持加载 |
| `shell` | 否 | 仅影响新窗格/窗口 |
| `env` | 否 | 仅影响新窗格/窗口 |
| `session.*` | 否 | 会话设置需要重启 |

实现：[event_loop.py](../plmux/app/event_loop.py)（`_ConfigWatcher`）| [cmdline.py](../plmux/modes/cmdline.py)（`_do_reload_config`）

## 加载流程

1. 从 `plmux/config/defaults.json` 加载包默认值
2. 如果用户配置文件不存在，则从默认值创建
3. 将用户配置深度合并到默认值之上（嵌套字典递归合并）
4. 将结果解析为类型化的 `PlmuxConfig` 数据类

实现：[loader.py](../plmux/config/loader.py#L30-L38)

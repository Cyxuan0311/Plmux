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

## 字段说明

### 顶层字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `shell` | `list[str] \| null` | `null` | Shell 命令及参数；为 `null` 时使用系统默认 shell |
| `env` | `dict[str, str]` | `{}` | 传递给子 shell 的额外环境变量 |
| `theme` | `string` | `"default"` | 当前主题名称；参见[主题](themes.zh-CN.md) |
| `ui` | object | — | UI 渲染选项（见下文） |
| `keys` | object | — | 键绑定选项（见下文） |
| `session` | object | — | 会话持久化选项（见下文） |
| `extensions` | object | — | 扩展选项（见下文） |

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

## 加载流程

1. 从 `plmux/config/defaults.json` 加载包默认值
2. 如果用户配置文件不存在，则从默认值创建
3. 将用户配置深度合并到默认值之上（嵌套字典递归合并）
4. 将结果解析为类型化的 `PlmuxConfig` 数据类

实现：[loader.py](../plmux/config/loader.py#L30-L38)

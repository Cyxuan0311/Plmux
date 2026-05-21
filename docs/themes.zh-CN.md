# 主题

主题是控制 plmux 视觉外观的 JSON 数据。它们定义了状态栏、窗格边框、窗格标题、命令行和模式指示器的颜色与样式。

## 选择主题

在[配置](configuration.zh-CN.md)中设置 `theme` 字段：

```json
{
  "theme": "default"
}
```

或在运行时使用 `:theme` 命令切换：

```
:theme dracula
```

## 内置主题

plmux 附带以下内置主题：

| 主题 | 描述 |
|------|------|
| `default` | 绿色状态栏，深色窗格边框 |
| `dracula` | 深色背景上的紫色点缀 |
| `gruvbox` | 温暖的黄/橙色调 |
| `monokai` | 经典的深色编辑器绿色调色板 |
| `nord` | 冷色调蓝灰斯堪的纳维亚调色板 |
| `solarized` | 基于 Solarized 规范的青色/蓝绿色 |
| `tokyonight` | 蓝/紫夜城调色板 |
| `catppuccin` | 柔和薰衣草/粉彩调色板 |
| `ayu` | 深色背景上的温暖金色点缀 |
| `material` | 受 Material Design 启发的紫/粉点缀 |
| `one-dark` | 来自 One Dark 主题的紫/青点缀 |
| `rose-pine` | 柔和紫/金自然调色板 |
| `everforest` | 柔和粉/绿森林调色板 |
| `kanagawa` | 紫/蓝日式灵感调色板 |
| `cyberpunk` | 霓虹粉/绿未来调色板 |
| `oceanic-next` | 紫/青海洋调色板 |
| `base16` | 柔和紫/绿 base16 调色板 |
| `alabaster` | 清爽亮色主题，柔和灰色调 |
| `apprentice` | 低对比度深色主题，适合长时间编码 |
| `horizon` | 大胆粉/红点缀，深色背景 |
| `papercolor` | 受 PaperColor Vim 启发的亮色主题 |
| `vscode-dark` | 受 VS Code 深色主题启发的蓝色状态栏 |
| `green-screen` | 磷光绿单色复古终端 |

实现：[theme.py](../plmux/ui/theme.py#L56-L537)

## 主题字段

主题 JSON 对象包含以下部分：

### `name`

主题的显示名称。

### `mode` — 模式指示器样式

| 字段 | 用途 |
|------|------|
| `mode.normal` | 普通模式指示器样式 |
| `mode.prefix` | 前缀模式指示器样式 |
| `mode.cmdline` | 命令行模式指示器样式 |

### `status` — 状态栏样式

| 字段 | 用途 |
|------|------|
| `status.style` | 状态栏品牌段样式 |
| `status.muted` | 状态栏次要文本样式 |
| `status.background` | 状态栏背景颜色 |
| `status.win` | 窗口段样式 |
| `status.pane` | 窗格段样式 |
| `status.clock` | 时钟段样式 |
| `status.host` | 主机段样式 |
| `status.command` | 前台命令段样式 |

### `pane` — 窗格样式

| 字段 | 用途 |
|------|------|
| `pane.active_border` | 聚焦窗格边框颜色 |
| `pane.inactive_border` | 非聚焦窗格边框颜色 |
| `pane.title_active` | 激活窗格标题样式 |
| `pane.title_inactive` | 非激活窗格标题样式 |

### `cmdline` — 命令行样式

| 字段 | 用途 |
|------|------|
| `cmdline.indicator` | 命令指示器样式 |
| `cmdline.body` | 命令输入样式 |
| `cmdline.background` | 命令行背景颜色 |
| `cmdline.indicator_fg` | 命令指示器前景颜色 |

### 自定义键

未识别的键会保留在 `Theme.extra` 中，便于试验新功能。这允许你添加自定义字段而不会破坏主题加载器。

实现：[theme.py `_parse_theme_data`](../plmux/ui/theme.py#L540-L567)

## 自定义主题

用户主题从用户配置目录中的 `themes.json` 文件加载：

| 平台 | 路径 |
|------|------|
| Linux / macOS | `~/.config/plmux/themes.json` |
| Windows | `%APPDATA%\plmux\themes.json` |

该文件应包含一个 JSON 对象，其中每个键是主题名称，值遵循上述主题字段结构。与内置主题同名的用户主题会覆盖内置主题。

示例 `themes.json`：

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

## 样式语法

样式使用 Rich 的样式语法。常见模式：

| 语法 | 含义 |
|------|------|
| `bold` | 粗体文本 |
| `dim` | 暗淡文本 |
| `white` | 命名前景色 |
| `on #hex` | 十六进制背景色 |
| `bold white on #333` | 组合：深灰背景上的粗体白色文本 |

实现：[theme.py](../plmux/ui/theme.py)

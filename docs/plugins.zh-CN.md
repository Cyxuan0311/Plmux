# 插件系统

plmux 提供了类 tmux 的插件扩展系统，允许你挂钩应用生命周期事件、注册自定义命令、添加键绑定和扩展状态栏。

## 配置

在 `config.json` 中启用插件：

```json
{
  "extensions": {
    "enabled": ["my-plugin", "another-plugin"],
    "search_paths": ["~/.config/plmux/extensions"]
  }
}
```

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enabled` | `list[str]` | `[]` | 启动时加载的插件名称列表 |
| `search_paths` | `list[str]` | `["~/.config/plmux/extensions"]` | 搜索插件的目录 |

## 插件发现

当插件名称列在 `enabled` 中时，plmux 按以下顺序搜索：

1. **Python 包**：`plmux_extensions.<name>`（可通过 pip 安装）
2. **含 `__init__.py` 的目录**：`<search_path>/<name>/__init__.py`
3. **含 `main.py` 的目录**：`<search_path>/<name>/main.py`
4. **单文件**：`<search_path>/<name>.py`

找到第一个匹配项即加载。如果未找到匹配项，会记录警告并继续启动。

## 插件结构

插件本质上是一个 Python 模块，在导入时调用注册函数即可。无需特殊的类或装饰器。

### 单文件插件

```
~/.config/plmux/extensions/
└── hello.py
```

```python
from plmux.extensions import register_hook, register_command, ExtensionContext

def on_start(ctx: ExtensionContext) -> None:
    print("Hello from hello plugin!")

register_hook("app_started", on_start)
```

### 目录插件

```
~/.config/plmux/extensions/
└── my-plugin/
    ├── __init__.py
    └── helpers.py
```

`__init__.py`：

```python
from plmux.extensions import register_hook, register_command, ExtensionContext
from .helpers import greet

def on_start(ctx: ExtensionContext) -> None:
    greet("my-plugin loaded")

def cmd_greet(ws, args) -> None:
    from plmux.input.commands import CommandResult
    name = args[0] if args else "world"
    return CommandResult(f"Hello, {name}!")

register_hook("app_started", on_start)
register_command("greet", cmd_greet)
```

## 钩子参考

钩子是接收 `ExtensionContext` 的回调函数，在特定事件发生时被调用。

### ExtensionContext 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `hook_name` | `str` | 触发此回调的钩子名称 |
| `extra_config` | `dict` | `config.json` 中的未知顶层键 |
| `pane_index` | `int` | 受影响的窗格索引（不适用时为 `-1`） |
| `window_index` | `int` | 受影响的窗口索引（不适用时为 `-1`） |
| `mode` | `str` | 当前模式字符串（如 `"NORMAL"`、`"PREFIX"`） |
| `command` | `str` | 命令相关钩子的命令名 |
| `message` | `str` | 附加上下文消息 |

### 可用钩子

| 钩子 | 触发时机 | 上下文字段 |
|------|---------|-----------|
| `app_started` | 应用完成初始化 | `extra_config` |
| `app_stopping` | 应用即将退出 | `extra_config` |
| `pane_created` | 新窗格创建 | `pane_index` |
| `pane_closed` | 窗格关闭 | `pane_index` |
| `pane_focus_changed` | 焦点切换到其他窗格 | `pane_index`、`message`（上一个窗格索引） |
| `window_created` | 新窗口创建 | `window_index`、`pane_index` |
| `window_closed` | 窗口关闭 | `window_index` |
| `mode_changed` | 输入模式变更 | `mode` |
| `session_saved` | 会话状态保存到磁盘 | — |
| `session_loaded` | 会话状态从磁盘恢复 | — |
| `command_executed` | 执行 `:` 命令 | `command` |
| `command_unknown` | 输入未识别的命令 | `command` |
| `status_refresh` | 状态栏即将刷新 | — |

### 注册钩子

```python
from plmux.extensions import register_hook, ExtensionContext

def on_pane_created(ctx: ExtensionContext) -> None:
    print(f"Pane {ctx.pane_index} created")

register_hook("pane_created", on_pane_created)
```

同一事件可以注册多个钩子，按注册顺序调用。如果某个钩子抛出异常，会记录日志并继续执行剩余钩子。

## 插件 API

### register_command(name, fn)

注册自定义 `:` 命令。

处理函数签名为 `fn(ws: PaneWorkspace, args: list[str]) -> CommandResult`。

```python
from plmux.extensions import register_command
from plmux.input.commands import CommandResult

def cmd_echo(ws, args) -> CommandResult:
    return CommandResult(" ".join(args) if args else "")

register_command("echo", cmd_echo)
```

加载此插件后，用户可以在命令行中输入 `:echo hello world`。

### register_key_binding(key, fn)

注册键绑定处理函数。

处理函数签名为 `fn(ws: PaneWorkspace) -> None`。

```python
from plmux.extensions import register_key_binding

def toggle_feature(ws) -> None:
    pass

register_key_binding("ctrl+g", toggle_feature)
```

### register_status_item(name, style)

向状态栏添加自定义项。

```python
from plmux.extensions import register_status_item

register_status_item("git-branch", "bold magenta on default")
```

### register_hook(name, fn)

为钩子事件注册回调（参见上方钩子参考）。

## 与 tmux 插件系统对比

| 功能 | tmux | plmux |
|------|------|-------|
| 钩子事件 | `@plugin` + TPM | `register_hook()` |
| 自定义命令 | `run-shell` | `register_command()` |
| 键绑定 | `bind-key` | `register_key_binding()` |
| 状态栏项 | `#{...}` 格式 | `register_status_item()` |
| 插件管理器 | TPM（第三方） | 内置 `extensions.enabled` |
| 搜索路径 | `TMUX_PLUGIN_MANAGER_PATH` | `extensions.search_paths` |
| 自动加载 | TPM `@plugin` 列表 | `extensions.enabled` 列表 |

## 示例插件

### 状态栏显示 Git 分支

```python
# ~/.config/plmux/extensions/git-branch.py
import subprocess
from plmux.extensions import register_hook, register_status_item, ExtensionContext

def refresh_git(ctx: ExtensionContext) -> None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=1,
        )
        branch = result.stdout.strip()
        if branch:
            register_status_item(f"git:{branch}", "bold magenta on default")
    except Exception:
        pass

register_hook("status_refresh", refresh_git)
```

### 会话保存通知

```python
# ~/.config/plmux/extensions/notify.py
from plmux.extensions import register_hook, ExtensionContext

def on_save(ctx: ExtensionContext) -> None:
    print("\a")  # 终端响铃

def on_load(ctx: ExtensionContext) -> None:
    print("会话已恢复。")

register_hook("session_saved", on_save)
register_hook("session_loaded", on_load)
```

### 带自动补全的自定义命令

```python
# ~/.config/plmux/extensions/project.py
from plmux.extensions import register_command
from plmux.input.commands import CommandResult

PROJECTS = {"work": "~/work", "personal": "~/projects"}

def cmd_project(ws, args) -> CommandResult:
    if not args:
        return CommandResult("用法: :project <名称>")
    name = args[0]
    path = PROJECTS.get(name)
    if not path:
        return CommandResult(f"未知项目: {name}")
    for session in ws.sessions:
        session.write(f"cd {path}\n".encode())
    return CommandResult(f"已切换到 {name}")

register_command("project", cmd_project)
```

实现：[registry.py](../plmux/extensions/registry.py)

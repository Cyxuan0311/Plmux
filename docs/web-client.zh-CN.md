# Web 客户端

plmux 内置 Web 服务器，通过 WebSocket 提供基于浏览器的终端访问。你可以从任何拥有浏览器的设备与 plmux 会话进行交互。

## 启动 Web 服务器

在 plmux 内部，使用 `:web` 命令：

```
:web              # 在默认端口 9888 启动
:web 8080         # 在自定义端口启动
```

停止服务器：

```
:webstop
```

然后在浏览器中打开 `http://localhost:9888`（或你自定义的端口）。

## 功能

- **完整终端仿真**: 基于 xterm.js 的渲染，支持 ANSI 颜色
- **键盘输入**: 支持所有标准按键、Ctrl 组合键、Alt 组合键、功能键和方向键
- **动态调整大小**: 终端自动调整以适应浏览器窗口
- **主题同步**: Web 客户端反映当前 plmux 主题颜色
- **状态栏**: 实时显示模式、窗口、窗格和前台命令
- **粘贴支持**: 通过浏览器从剪贴板粘贴文本

## 键盘支持

Web 客户端将浏览器键盘事件映射为终端转义序列：

| 浏览器按键 | 终端序列 |
|-----------|---------|
| `Enter` | `\r`（回车） |
| `Backspace` | `\x7f`（DEL） |
| `Tab` | `\t` |
| `Escape` | `\x1b` |
| `方向键 上/下/左/右` | `\x1b[A/B/C/D` |
| `Home` / `End` | `\x1b[H` / `\x1b[F` |
| `Delete` / `Insert` | `\x1b[3~` / `\x1b[2~` |
| `PageUp` / `PageDown` | `\x1b[5~` / `\x1b[6~` |
| `F1`–`F12` | `\x1b[11~` / `\x1b[12~` / ... |
| `Ctrl+A`–`Ctrl+Z` | `\x01`–`\x1a` |
| `Ctrl+[` / `Ctrl+]` / `Ctrl+\` | `\x1b` / `\x1d` / `\x1c` |
| `Alt+<键>` | `\x1b<键>` |

实现：[web/__init__.py](../plmux/web/__init__.py) — `_web_key_to_terminal()`

## 架构

### WebSocket 通信

Web 服务器使用自定义 WebSocket 实现（无外部依赖）：

1. **HTTP 服务器**: 基于 `asyncio.start_server` — 在 `GET /` 上提供 HTML 页面，在 `GET /ws` 上升级为 WebSocket
2. **帧解析器**: 解析来自浏览器客户端的 WebSocket 帧
3. **帧编码器**: 将传出消息编码为 WebSocket 文本帧

### C 扩展加速

当 C 扩展（`_ws_kernel`）可用时，WebSocket 帧的解析和编码在 C 中处理，以提高性能：

- `FrameParser`: 增量帧解析器，提供 `feed()` + `parse()` API
- `encode_text_frame()`: 将文本数据编码为 WebSocket 帧
- `encode_binary_frame()`: 将二进制数据编码为 WebSocket 帧
- `encode_close_frame()`: 编码关闭帧
- `encode_pong_frame()`: 编码 pong 响应

当 C 扩展不可用时，自动使用纯 Python 回退实现。

实现：[web/_c_extension/](../plmux/web/_c_extension/)

### 消息协议

Web 客户端通过 WebSocket 使用 JSON 消息通信：

**客户端 → 服务器：**

| 类型 | 字段 | 描述 |
|------|------|------|
| `key` | `key`, `ctrl`, `alt`, `shift`, `code` | 键盘事件 |
| `input` | `data` | 原始文本输入 |
| `paste` | `text` | 粘贴的文本 |
| `ready` | `cols`, `rows` | 客户端初始化及终端尺寸 |
| `resize` | `cols`, `rows` | 浏览器窗口大小变化 |

**服务器 → 客户端：**

| 类型 | 字段 | 描述 |
|------|------|------|
| `output` | `data` | 终端输出（ANSI 文本） |
| `snapshot` | `data` | 连接时的初始屏幕内容 |
| `status` | `mode`, `win`, `pane`, `cmd`, `clock`, `host` | 状态栏更新 |
| `theme` | `name`, `mode`, `status`, `pane`, `cmdline` | 主题颜色数据 |

### 输出管道

PTY 会话的终端输出通过高效管道传输到 Web 客户端：

1. PTY 输出通过每个 `TerminalSession.stream` 上的输出钩子捕获
2. 输出块被放入 `asyncio.Queue` 队列
3. 排水循环以 33ms 间隔批量处理块并广播给所有连接的客户端
4. 当 C 扩展可用时，帧直接在 C 中编码

实现：[web/server.py](../plmux/web/server.py) — `_broadcast_loop()`

## 安全注意事项

- Web 服务器默认绑定到 `0.0.0.0`，可从任何网络接口访问
- 如需仅本地访问，启动 `:web` 后确保防火墙阻止外部对端口 9888 的访问
- **没有身份验证** — 任何能访问该端口的人都有完整的终端访问权限
- 在共享或公共网络上使用时请谨慎

## 限制

- 鼠标事件不会转发到终端（依赖鼠标的 TUI 应用可能无法正常工作）
- 回滚缓冲区仅限于当前屏幕内容
- 多个浏览器客户端共享相同的终端会话（无多路复用）

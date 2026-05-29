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
- **TLS/HTTPS**: 通过可配置的 SSL/TLS 证书实现加密远程访问
- **Token 认证**: 使用读写 Token 和只读 Token 进行安全访问控制
- **会话路由**: 通过 URL 路径直接访问指定会话（如 `/session/my-session`）
- **只读模式**: 分享会话供观察，不允许输入操作

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

## 远程访问

plmux 支持从浏览器或其他终端安全地远程访问终端会话。

### TLS/HTTPS

在配置文件中配置 TLS 证书和私钥以启用 HTTPS：

```json
{
  "web": {
    "host": "0.0.0.0",
    "port": 9888,
    "tls_cert": "/path/to/cert.pem",
    "tls_key": "/path/to/key.pem"
  }
}
```

配置 TLS 后，Web 服务器自动使用 HTTPS，WebSocket 连接升级为 `wss://`。最低 TLS 版本为 1.2。

### Token 认证

启用基于 Token 的认证以限制访问：

```json
{
  "web": {
    "auth_enabled": true,
    "tokens": ["my-secret-rw-token"],
    "readonly_tokens": ["observer-token"]
  }
}
```

- **读写 Token**（`tokens`）：完整的终端访问权限，包括输入
- **只读 Token**（`readonly_tokens`）：仅查看权限 — 所有键盘输入、粘贴和调整大小操作均被阻止

Token 可通过以下方式提供：
- URL 查询参数：`https://server:9888/?token=my-secret-rw-token`
- HTTP 请求头：`Authorization: Bearer my-secret-rw-token`

### Token 管理面板

使用 `:web-token` 命令打开交互式 Overlay 面板管理 Token：

```
:web-token
```

| 按键 | 操作 |
|------|------|
| `g` | 生成读写 Token |
| `r` | 生成只读 Token |
| `d` | 撤销选中的 Token |
| `y` | 复制最近生成的 Token 到剪贴板 |
| `↑` / `k` | 上移光标 |
| `↓` / `j` | 下移光标 |
| `Home` | 跳到顶部 |
| `G` | 跳到底部 |
| `Esc` / `q` | 关闭面板 |

面板显示所有活跃 Token 的前缀、哈希和模式（读写或只读）。新生成的 Token 显示在面板底部，可通过 `y` 复制。

### 会话路由

通过 URL 路径直接访问指定会话：

```
https://server:9888/session/my-session?token=xxx
```

这将打开 Web 客户端并聚焦到指定名称的会话。

### 状态指示器

Web 客户端状态栏显示安全指示器：

- **🔒 TLS** — 通过 HTTPS 连接时显示（绿色徽章）
- **🔒 READ-ONLY** — 使用只读 Token 认证时显示（红色徽章）

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
| `focus` | `idx` | 焦点切换到窗格 `idx` |
| `resize_pane` | `idx`, `rows` | 调整窗格 `idx` 为 `rows` 行 |

**服务器 → 客户端：**

| 类型 | 字段 | 描述 |
|------|------|------|
| `output` | `data` | 终端输出（ANSI 文本） |
| `snapshot` | `data` | 连接时的初始屏幕内容 |
| `status` | `mode`, `win`, `pane`, `cmd`, `clock`, `host` | 状态栏更新 |
| `theme` | `name`, `mode`, `status`, `pane`, `cmdline` | 主题颜色数据 |
| `layout` | `tree`, `focus`, `panes` | 布局结构更新 |
| `mode` | `mode`, `prev_mode` | 模式变更通知 |
| `overlay` | `kind`, `content` | Overlay 面板显示 |
| `overlay_close` | | 关闭 Overlay 面板 |

### 输出管道

PTY 会话的终端输出通过高效管道传输到 Web 客户端：

1. PTY 输出通过每个 `TerminalSession.stream` 上的输出钩子捕获
2. 输出块被放入 `asyncio.Queue` 队列
3. 排水循环以 33ms 间隔批量处理块并广播给所有连接的客户端
4. 当 C 扩展可用时，帧直接在 C 中编码

实现：[web/server.py](../plmux/web/server.py) — `_broadcast_loop()`

## 安全注意事项

- Web 服务器默认绑定到 `0.0.0.0`，可从任何网络接口访问
- 如需仅本地访问，在 web 配置中设置 `"host": "127.0.0.1"` 或确保防火墙阻止外部对端口 9888 的访问
- **Token 认证**已可用 — 在 web 配置中启用 `auth_enabled` 并配置 `tokens` 和 `readonly_tokens`
- **TLS/HTTPS**已支持 — 配置 `tls_cert` 和 `tls_key` 可加密所有流量
- 未启用认证时，任何能访问该端口的人都有完整的终端访问权限
- 只读 Token 允许分享会话供观察，而不授予输入能力
- Token 以 SHA-256 哈希存储 — 明文 Token 仅在生成时显示一次

## 限制

- 鼠标事件不会转发到终端（依赖鼠标的 TUI 应用可能无法正常工作）
- 回滚缓冲区仅限于当前屏幕内容
- 多个浏览器客户端共享相同的终端会话（无多路复用）

# Release Notes

## v0.1.0 — Initial Release

### 核心功能
- 多窗口/窗格 tmux 会话管理
- 命令行模式 (`:` 快捷键) 与 tab 补全
- 命令别名支持
- 插件系统（加载/卸载/配置）
- 配置文件自动重载
- 鼠标事件支持（选择、调整大小、滚动）
- 复制模式（scrollback 搜索、选择、复制）
- 格式变量替换引擎 (`{session_name}`, `{window_name}`, `{pane_index}` 等)
- 缓冲区管理器
- 钩子系统（`on_pre_exec`, `on_post_exec`, `on_pane_focus` 等事件）
- IPC 支持（daemon 模式）

### 用户界面
- 内存使用量覆盖层 (`:memory`) — 树形展示进程/会话/窗口/窗格，渐变进度条
- 时钟覆盖层（适应窗格宽度）
- 宠物/RPG 状态面板（HP/ATK/DEF/SPD/INT）
- 文件浏览器插件（图标、目录展开、滚动）
- Web Token 管理覆盖层
- 窗格样式 & 状态栏样式配置界面
- 状态栏梯度渐变显示
- 圆角 / 边框主题支持

### Web 客户端
- 内置 Web 服务器，支持远程访问
- 身份验证（JWT Token）
- 只读模式
- 会话路由与管理
- 窗格缩放、终端字体优化
- 新的连接界面和覆盖层处理

### 主题
- 内置 20+ 主题 (`ayu`, `nord`, `dracula`, `solarized` 等)
- 主题热切换 (`:theme <name>`)

### 开发 & 工程
- 事件循环分解为 6 个专注模块
- 完整的鼠标处理模块分离
- 工作区 / 窗格 / 会话抽象层
- Windows / Linux / macOS 兼容性处理
- CI 工作流 (GitHub Actions)
- pytest 测试套件

### 修复
- 修复循环导入问题
- 修复测试 mock 覆盖问题
- 修复 Windows spawn 标志兼容性
- 清理未使用的导入和死代码

### 文档
- 中英文双语文档：配置、快捷键、主题、插件、Web 客户端
- 鼠标操作指南
- 复制模式使用说明

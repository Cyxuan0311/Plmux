# Copy Mode — 交互式文本选择

Copy mode 允许你在终端中选择和复制文本内容。

## 快捷键

| 按键 | 行为 |
|------|------|
| `Prefix + [` | 进入 copy-mode |
| `Esc` 或 `q` | 退出 copy-mode |
| 方向键 | 移动选择光标 |
| `PageUp` | 向上翻页（移动可见窗格高度） |
| `PageDown` | 向下翻页（移动可见窗格高度） |
| `Home` | 移动到当前行行首 |
| `End` | 移动到当前行行尾 |
| `V` | 切换行选择模式 |
| `y` | 复制选区到剪贴板并退出 |
| 鼠标点击+拖拽 | 通过拖拽选择文本（自动进入 copy mode） |

## 选择模式

- **字符选择**（默认）：逐字符选择
- **行选择**：按 `V` 切换，选择整行

## 鼠标支持

在窗格中点击并拖拽会自动进入 copy mode 并创建选区。选区锚点设置在点击位置，光标跟随拖拽。释放鼠标按钮结束拖拽但保持在 copy mode 中 — 按 `y` 复制或 `Esc`/`q` 退出。

在 copy mode 中使用鼠标滚轮可以上下滚动回滚缓冲区内容。当滚动到最底部时，自动退出 copy mode 回到正常模式。

## 实现细节

### 选区表示

- 使用 `(row, col)` 半开区间表示选区
- 支持跨行选择
- 支持反向选择（起点可以在终点之后）

### 渲染

- 选中文本应用 `reverse` 样式高亮
- 选区边界通过 TerminalSession 的公共属性 `copy_sel_start` 和 `copy_sel_end` 管理

### 剪贴板集成

复制时使用以下优先级：

1. `pyperclip`（主要方式）
2. 平台回退：
   - macOS: `pbcopy`
   - Windows: `clip`
   - Linux: `xclip`

实现：[clipboard.py](../plmux/platform/clipboard.py)

## 注意事项

- 在无 X11 环境下（如纯 SSH 会话），剪贴板回退可能无效
- Copy 操作为 best-effort，不保证在所有环境下都能成功

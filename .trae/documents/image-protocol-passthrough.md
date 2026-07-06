# Sixel/Kitty 图像协议透传实现计划

## 概述

使 plmux 支持类似 tmux 的 Sixel/Kitty 图像协议透传，让运行在 PTY 中的应用程序（如 `chafa`、`kitty +kitten icat`、`viu` 等）能通过 plmux 在宿主终端中正确显示内联图像。

**核心思路**：参考 tmux 的 `allow-passthrough` 机制，在 PTY 输出流中识别 DCS（Sixel）和 APC（Kitty）图像序列，将原始图像数据直接透传到宿主终端，同时正确处理坐标偏移（面板在宿主终端中的绝对位置）。

---

## 现状分析

### 当前渲染管线

```
PTY 输出 → _reader_loop → _read_queue → _pump_queue → stream.feed(data)
  → C 解析器(VT500状态机) → FastScreen 缓冲区(FastCell数组)
  → build_render_text() → render_row_to_ansi() → TerminalContent(Rich Renderable)
  → Rich Live → 宿主终端
```

### 关键障碍

1. **C 解析器丢弃 DCS/APC 数据**：
   - `ST_DCS_DATA` 状态：641-765 行，数据全部忽略，仅检测 ST 终止符
   - `ST_SOS_PM_APC` 状态：775-779 行，APC 数据直接丢弃
   - `dcs_collect` 仅 8 字节，无法缓存 Sixel 数据
   - `osc_buf` 仅 256 字节

2. **FastCell 无图像占位概念**：24 字节结构只存 codepoint + 样式，无法标记"此位置有图像"

3. **渲染管线无原始字节直出通道**：所有输出必须经过 Rich 的文本渲染管线

4. **坐标映射缺失**：面板使用虚拟坐标，需要映射到宿主终端的绝对坐标

### tmux 的两种方案对比

| 方案 | 原理 | 优点 | 缺点 |
|------|------|------|------|
| **Sixel 原生解码** | 解码→存储→重编码 | 完美滚动/切换/重绘支持 | 实现复杂度极高，需要 Sixel 解码器 |
| **Passthrough 透传** | 原始序列直接转发 | 实现简单，与 tmux 一致 | 窗格切换/滚动时图像可能残留(ghosting) |

**选择 Passthrough 方案**，理由：
1. 与 tmux 当前默认行为一致（tmux 的 Kitty 协议也只走 passthrough）
2. 实现复杂度低，不需要内嵌 Sixel 解码器
3. 后续可渐进式添加 Sixel 原生支持

---

## 实现方案

### 架构设计

采用**双轨渲染**架构：

```
PTY 输出 → _reader_loop → _read_queue
  ↓
_pump_queue() 中分叉:
  ├─ 非图像数据 → stream.feed(data) → 原有管线(不变)
  └─ 图像序列   → 缓存完整序列 → passthrough 队列
       ↓
渲染时:
  ├─ 文本内容: TerminalContent(Rich Renderable) → 原有管线
  └─ 图像数据: 坐标偏移后直接写入 term.stream
```

### 阶段 1：C 解析器改造 — 捕获 DCS/APC 数据

**文件**: `plmux/terminal/_c_extension/_fastscreen_types.h`

1. 扩展 `FastParser` 结构体：
   - 添加动态缓冲区 `dcs_buf`(char*) + `dcs_buf_size`(int) + `dcs_buf_cap`(int)，用于缓存 DCS 数据（Sixel）
   - 添加动态缓冲区 `apc_buf`(char*) + `apc_buf_size`(int) + `apc_buf_cap`(int)，用于缓存 APC 数据（Kitty）
   - 添加 `dcs_params_buf`(char[64]) + `dcs_params_len`(int)，缓存 DCS 参数部分
   - 添加 `passthrough_flag`(int) 标记是否有待取走的透传数据

2. 添加回调函数指针：
   - `on_dcs_complete`(回调，接收参数+数据体)
   - `on_apc_complete`(回调，接收APC数据体)

**文件**: `plmux/terminal/_c_extension/_fastscreen_parser.c`

3. 修改 `ST_DCS_ENTRY` 状态：缓存参数字节到 `dcs_params_buf`
4. 修改 `ST_DCS_DATA` 状态：将数据体字节追加到 `dcs_buf`，而非丢弃
5. 修改 DCS 终止（收到 ST/BEL）：调用 `on_dcs_complete` 回调
6. 修改 `ST_SOS_PM_APC` 状态：APC 以 `ESC _` 开头，区分 `_`(APC) 与其他（SOS/PM），将 APC 数据缓存到 `apc_buf`
7. APC 终止时调用 `on_apc_complete` 回调

**文件**: `plmux/terminal/_c_extension/_fastscreen_module.c`

8. 在 Python 模块中注册回调，将 DCS/APC 数据通过 Python 回调传递给 Python 层

### 阶段 2：Python 层透传管线

**文件**: `plmux/terminal/session.py`

1. 在 `TerminalSession` 中添加：
   - `_passthrough_queue: list[bytes]` — 待透传的完整图像序列（带原始转义前缀）
   - `_passthrough_lock: threading.Lock` — 保护队列
   - `_in_image_seq: bool` — 标记是否正在接收图像序列
   - `_image_seq_buf: bytearray` — 图像序列缓冲

2. 在 `_pump_queue()` / `feed()` 中：
   - 在调用 `stream.feed(data)` 之前，先扫描数据中的 DCS/APC 序列
   - 将非图像数据照常喂入解析器
   - 将图像序列数据缓存到 `_image_seq_buf`，完成后放入 `_passthrough_queue`
   - 同时在屏幕缓冲区中为图像占据的区域写入占位空格（保持光标位置正确）

3. 提供 `drain_passthrough()` 方法：供渲染层取走所有待透传的原始序列

**策略选择 — 前扫描 vs 后回调**：

采用**前扫描**方案（在 Python 层 `_pump_queue` 中预处理原始字节流），原因：
- 避免修改 C 解析器的回调机制，降低复杂度
- 图像序列在原始字节层面很容易识别（`ESC P` / `ESC _`）
- 保持 C 解析器不变，仅做兼容性扩展

### 阶段 3：图像序列识别与提取

**文件**: 新增 `plmux/terminal/image_passthrough.py`

1. 实现图像序列扫描器 `ImageSeqScanner`：
   - 输入: 原始字节流
   - 输出: 分割后的 `[(text_data, image_data), ...]` 列表
   - 识别 Sixel: `ESC P ... q ... ST` (DCS with final byte 'q')
   - 识别 Kitty: `ESC _ G ... ST` (APC with 'G' prefix)
   - 正确处理嵌套 ESC（DCS/APC 内部的 ESC 需特殊处理）

2. 序列分类：
   - Sixel DCS: `ESC P <params> q <sixel_data> ESC \` 或 `ESC P <params> q <sixel_data> BEL`
   - Kitty APC: `ESC _ G <kitty_data> ESC \` 或 `ESC _ G <kitty_data> BEL`
   - 其他 DCS: 不透传，照常由解析器处理

3. Kitty 协议特殊处理：
   - 支持 `U=1` 模式（Unicode 占位符），这是在多路复用器中最佳的 Kitty 图像显示方式
   - 当检测到 Kitty 图像序列时，提取 image_id，供后续占位符匹配使用

### 阶段 4：坐标偏移与渲染集成

**文件**: `plmux/ui/renderer.py`, `plmux/app/event_loop.py`

1. 计算面板在宿主终端中的绝对位置：
   - 当前面板的 `Tree` 节点包含矩形区域 `(x, y, w, h)`
   - Rich Panel 边框占用 1 行/列，内容区偏移 = `(x + 1, y + 1)`
   - 绝对光标位置 = 面板偏移 + 面板内光标位置

2. 渲染时在文本内容之后输出图像：
   - 在 `live.update(root)` 之后，如果有待透传的图像数据：
     - 先保存当前光标位置: `ESC 7`
     - 移动到图像起始绝对位置: `ESC[row;colH`
     - 输出原始图像序列
     - 恢复光标位置: `ESC 8`

3. 图像序列中的坐标修正：
   - Kitty 协议的 `a=T`（placement）参数需要修正行/列偏移
   - Sixel 无坐标概念，依赖光标位置，需在透传前正确设置光标

### 阶段 5：终端能力检测与查询拦截

**文件**: 新增 `plmux/terminal/capabilities.py`

1. 宿主终端能力检测：
   - 检测 Sixel 支持：发送 `DA1` 查询（`\x1b[c`），检查响应中 bit 2
   - 检测 Kitty 支持：发送 `\x1b[?62;c`（kitty DA 查询），检查响应
   - 缓存检测结果

2. PTY 侧查询拦截：
   - 子进程可能发送 `DA1` 查询检测终端能力
   - 需要拦截这些查询并伪造响应，使子进程"看到"宿主终端的图像能力
   - 在 `TerminalSession` 中拦截 PTY 输出中的 DA 响应请求
   - 根据 `_passthrough_enabled` 配置和宿主终端能力，构造正确的 DA 响应写回 PTY

3. 环境变量设置：
   - 在 PTY 环境中设置 `TERM` 正确值
   - 设置 `COLORTERM=truecolor`（如果宿主终端支持）
   - Kitty 环境下设置 `TERM=xterm-kitty`

### 阶段 6：配置与 Ghosting 缓解

**文件**: `plmux/config/schema.py`

1. 添加配置项：
   ```json
   {
     "image": {
       "passthrough": true,        // 是否启用图像透传，默认 true
       "sixel": true,              // 是否透传 Sixel，默认 true
       "kitty": true,              // 是否透传 Kitty APC，默认 true
       "clear_on_switch": true     // 切换面板时是否清除图像残留
     }
   }
   ```

2. Ghosting 缓解策略（窗格切换时图像残留）：
   - 切换到其他面板时，发送 `ESC[2J` 或 Kitty 的 `\x1b_Ga=d,d=I` 删除图像
   - 切回时重新发送图像序列（需缓存最近一次透传的数据）
   - 滚动时类似处理

### 阶段 7：C 解析器 DCS/APC 透传兼容

**文件**: `plmux/terminal/_c_extension/_fastscreen_parser.c`

为了使 C 解析器在透传模式下正确处理光标位置，需修改：

1. Sixel DCS 结束后，需要将光标移到图像下方：
   - Sixel 图像的高度可以通过解析 Sixel 参数中的宽高信息推算
   - 或简化处理：DCS 结束后不清除 `dcs_collect`，让 Python 层处理光标偏移

2. APC (Kitty) 结束后：
   - Kitty 使用 `a=p`（pixel placement）时不移动光标
   - 使用 `a=T`（cell placement）时需要移动光标
   - 在屏幕缓冲区中标记图像占位区域

---

## 实施步骤（按优先级排序）

### Step 1: 图像序列扫描器
- 新建 `plmux/terminal/image_passthrough.py`
- 实现 `ImageSeqScanner`，能从原始字节流中识别和提取 Sixel DCS / Kitty APC 序列
- 编写单元测试

### Step 2: TerminalSession 透传管线
- 修改 `session.py` 的 `_pump_queue()` 和 `feed()`
- 在喂入 C 解析器之前，先扫描并提取图像序列
- 图像序列存入 `_passthrough_queue`，非图像数据照常处理
- 对 Sixel 图像占据的行数做占位处理（写入空格并移动光标）

### Step 3: 坐标偏移与渲染集成
- 在 `event_loop.py` 的渲染循环中添加透传输出逻辑
- 计算面板绝对坐标，在 Rich 渲染完成后输出图像序列
- 处理光标保存/恢复

### Step 4: 终端能力检测
- 新建 `capabilities.py`
- 实现宿主终端 Sixel/Kitty 能力检测
- 实现 PTY 侧 DA 查询拦截与响应伪造

### Step 5: C 解析器改造（可选增强）
- 扩展 `dcs_collect` 为动态缓冲区
- 添加 APC 数据缓冲
- 在 Sixel DCS 结束后正确更新光标位置

### Step 6: Ghosting 缓解与配置
- 添加配置项
- 实现面板切换时的图像清除
- 缓存最近透传数据用于重绘

---

## 关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 透传 vs 原生解码 | Passthrough | 与 tmux 一致，实现简单 |
| 扫描位置 | Python 层前扫描 | 避免改 C 解析器回调，风险低 |
| Kitty 占位方案 | 支持 U=1 Unicode 占位 | tmux 兼容性最佳方案 |
| 光标处理 | 保存/恢复 + 绝对定位 | 简单可靠 |
| Ghosting 处理 | 切换时清除 + 缓存重绘 | 渐进式改善 |

---

## 验证步骤

1. **Sixel 基础测试**: 在 plmux 中运行 `chafa some.png`，确认图像正确显示在面板位置
2. **Kitty 基础测试**: 在 plmux 中运行 `kitty +kitten icat some.png`，确认图像正确显示
3. **多面板测试**: 分割面板后，两个面板同时显示图像，确认无错位
4. **面板切换测试**: 切换焦点面板，确认无 ghosting 残留
5. **滚动测试**: 图像在视口内滚动，确认不会破坏显示
6. **终端能力检测测试**: 在不同终端（Kitty/Sixel/无图像支持）中运行，确认正确检测和降级
7. **性能测试**: 大图像（>1MB）透传无卡顿

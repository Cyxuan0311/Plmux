# 修复 Sixel 图像屏闪与抖动

## Context

当 plmux 中显示 Sixel 图像时，存在明显的屏闪和抖动。根本原因是双轨渲染架构：

1. Rich `live.refresh()` 全屏重写 → 覆盖图像区域的像素数据
2. `_flush_image_passthrough()` 在 Rich 之后重发 2.4MB Sixel 数据 → 图像恢复

两者之间的空窗期产生可见闪烁，且 2.4MB 数据每帧重发导致性能问题。

调试日志显示：图像出现后约每 0.1~1 秒就重发一次 2.4MB，23 秒内写出了约 132MB 数据。

## 方案：跳过图像行渲染 + 按需重发

核心思路：让 Rich 在渲染时**跳过图像所在的行**（只输出换行符），这样图像不会被覆盖，就不需要每帧重发。

### 修改文件

1. **`plmux/terminal/session.py`** — 核心变更
   - 添加 `_image_rows: dict[int, list[int]]` 跟踪图像占用的行（key=seq_id, value=行号列表）
   - `_handle_image_seqs()` 中填充 `_image_rows`：Sixel 的 `start_row` ~ `start_row + estimated_rows - 1`
   - `_pump_queue()` 中处理滚动偏移：scroll_count 变化时调整 `_image_rows` 中的行号
   - `resize()` 中清空 `_image_rows`
   - 添加 `image_rows` 属性返回合并的 `set[int]`
   - `build_render_text()` 接受 `image_rows` 参数，对图像行输出空字符串而非 ANSI 内容
   - `TerminalContent` 接受 `image_rows` 参数，`__rich_console__()` 跳过图像行的渲染
   - `drain_passthrough()` 改为默认不返回缓存序列（因为图像不再被覆盖）

2. **`plmux/app/event_loop.py`** — `_flush_image_passthrough()` 修改
   - `drain_passthrough()` 默认只返回新序列
   - Ghosting mitigation 清除图像后，需要一次性重发缓存序列（通过 `include_cached=True` 参数）

3. **`plmux/ui/renderer.py`** — `_build_pane_panel()` 传递 `image_rows`
   - `build_render_text(image_rows=session.image_rows)`

4. **`plmux/terminal/image_passthrough.py`** — 添加 `estimate_kitty_rows()` 辅助函数

### 实施步骤

#### 1. 添加 `_image_rows` 跟踪（session.py）

在 `__init__`、`from_existing`、`create_remote` 三个构造方法中添加：

```python
self._image_rows: dict[int, list[int]] = {}  # seq_id -> [row indices]
self._image_seq_counter: int = 0
```

#### 2. 填充 `_image_rows`（session.py `_handle_image_seqs`）

```python
# 在现有 Sixel 处理后：
occupied_rows = list(range(seq.start_row, min(seq.start_row + rows, self.rows)))
if occupied_rows:
    self._image_seq_counter += 1
    seq_id = self._image_seq_counter
    # 移除重叠的旧图像行
    overlap_ids = [oid for oid, orows in self._image_rows.items()
                   if any(r in occupied_rows for r in orows)]
    for oid in overlap_ids:
        del self._image_rows[oid]
    self._image_rows[seq_id] = occupied_rows
```

#### 3. 滚动处理（session.py `_pump_queue`）

在 `_pump_queue()` 处理完数据后，检查 scroll_count 变化：

```python
if self._image_rows:
    scroll_delta = sc_after - sc_before
    if scroll_delta > 0:
        new_map = {}
        for sid, rows in self._image_rows.items():
            shifted = [r - scroll_delta for r in rows if r - scroll_delta >= 0]
            if shifted:
                new_map[sid] = shifted
        self._image_rows = new_map
```

#### 4. 清空条件

- `resize()` 中：`self._image_rows.clear()`
- alt-screen 切换时：在 `_pump_queue` 中检测 `use_alt_screen` 变化后清空

#### 5. `build_render_text()` 跳过图像行

```python
def build_render_text(self, *, ..., image_rows: set[int] | None = None):
    for y in range(self.rows):
        if image_rows and y in image_rows:
            lines.append("")
            continue
        # ... 现有逻辑 ...
    return TerminalContent(lines, self.cols, self.rows, image_rows=image_rows)
```

#### 6. `TerminalContent` 跳过图像行

```python
def __rich_console__(self, console, options):
    for i, line in enumerate(self._lines):
        if i in self._image_rows:
            if i < len(self._lines) - 1:
                yield Segment("\n", style=None)
            continue
        # ... 现有逻辑 ...
```

#### 7. `_build_pane_panel()` 传递 image_rows

```python
body = session.build_render_text(
    ..., image_rows=session.image_rows)
```

#### 8. `drain_passthrough()` 默认不返回缓存

```python
def drain_passthrough(self, *, include_cached: bool = False) -> list[ImageSeq]:
    with self._passthrough_lock:
        if self._passthrough_queue:
            seqs = self._passthrough_queue
            self._passthrough_queue = []
            self._last_passthrough_seqs = list(seqs)
            return seqs
        if include_cached and self._last_passthrough_seqs:
            return self._last_passthrough_seqs
        return []
```

#### 9. `_flush_image_passthrough()` 仅在 ghosting 清除后重发缓存

```python
images_were_cleared = False
if clear_on_switch and focus_changed:
    # ... delete all ...
    images_were_cleared = True

for pane_idx, session in enumerate(win.panes):
    seqs = session.drain_passthrough(include_cached=images_were_cleared)
```

#### 10. 添加 `estimate_kitty_rows()`（image_passthrough.py）

从 Kitty APC payload 中提取 `r`（行数）或 `s`（像素高度）参数来估算行数。

### 验证

1. 启动 plmux，运行 `chafa test.png`
2. 图像应稳定显示，无闪烁
3. 等待时钟更新，确认图像不被覆盖
4. 在另一个 pane 中运行命令，确认图像 pane 不闪烁
5. 测试切换 pane focus（ghosting mitigation 后图像正确恢复）
6. 测试 resize 后图像消失（符合预期）
7. 测试 scrollback 模式下正常显示文本

<div align="center">
  <img 
    src="resource/logo.png" 
    alt="plmux logo" 
    width="120" 
    style="border-radius: 16px; overflow: hidden;"
  />

# plmux ： Python Lightweight Terminal Multiplexer

[English](README.md) | 中文

[![Version](https://img.shields.io/badge/version-0.1.0-blueviolet.svg)](https://github.com/Frames/plmux/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-0078D4.svg)](https://github.com/Frames/plmux)

</div>



一个轻量级的跨平台终端复用工具，灵感来源于 tmux，基于 Python、Rich 和 C 扩展构建。提供窗格分割、窗口管理、复制模式、Vim 风格命令接口、动态状态栏（实时显示前台进程）、36 款内置主题、会话持久化、浏览器 Web 客户端，类 tmux 的插件扩展系统，以及配置热更新支持。

<div align="center">
  <img src="resource/demo.png" alt="plmux demo" />
  <p>plmux 在 Windows 终端中的操作演示(wsl2 环境)</p>
</div>

## 特性

- **窗格分割**: 支持垂直和水平分割，可调整比例
- **窗口管理**: 多窗口支持，可循环切换布局
- **窗格缩放**: 将任意窗格切换为全屏显示
- **布局模板**: 10 款内置布局模板（even-horizontal、main-vertical、quad、columns 等）
- **复制模式**: 文本选择和剪贴板集成
- **命令行**: Vim 风格的 `:` 命令接口，支持 Tab 补全
- **动态状态栏**: 实时显示模式、窗口、窗格、前台命令（nano、btop、fzf 等）、时钟和主机名
- **主题**: 36 款内置主题（dracula、gruvbox、tokyonight、catppuccin、nord、edge、doom-one、challenger-deep、moonlight、forest-night、snazzy 等）+ 用户自定义 JSON 主题
- **热更新**: 配置和插件变更自动检测并应用，无需重启
- **Web 客户端**: 通过 WebSocket 在浏览器中访问终端，C 扩展加速帧处理
- **插件系统**: 类 tmux 的扩展钩子、自定义命令、键绑定和状态栏项
- **C 扩展**: FastScreen（ANSI 解析/渲染）和 WebSocket 内核，用于高性能帧处理
- **跨平台**: 支持 Windows、macOS 和 Linux
- **会话持久化**: 自动保存和恢复布局
- **守护进程模式**: 分离会话到后台运行，随时重新连接

## 快速开始

### 安装

```bash
pip install .
```

或以开发模式安装：

```bash
pip install -e .
```

### 使用

```bash
plmux                  # 启动新会话
plmux ls               # 列出活动会话
plmux lsw              # 列出窗口
plmux lsw -p           # 列出窗口及窗格详情
plmux attach           # 连接到已有会话
plmux new-session      # 创建分离的会话
plmux kill-server      # 终止守护进程
```

## 快捷键

### 前缀键

所有快捷键均以 **Ctrl+B** 为前缀（可配置）。详见[快捷键](docs/keybindings.zh-CN.md)完整文档。

| 行为 | 绑定 |
|------|------|
| 前缀键 | `Ctrl+B` |
| 垂直分割 | 前缀 + `%` 或 `v` |
| 水平分割 | 前缀 + `"` 或 `s` |
| 切换焦点（hjkl） | 前缀 + `h` `j` `k` `l` |
| 切换焦点（方向键） | 前缀 + `←` `↓` `↑` `→` |
| 仅保留当前窗格 | 前缀 + `o` |
| 缩放窗格 | 前缀 + `z` |
| 新建窗口 | 前缀 + `c` |
| 下/上一个窗口 | 前缀 + `n` / `p` |
| 跳转到窗口 0-9 | 前缀 + `0`-`9` |
| 循环切换布局 | 前缀 + `Space` |
| 进入复制模式 | 前缀 + `[` |
| 调整窗格大小 | 前缀 + `H` `J` `K` `L` |
| 显示帮助 | 前缀 + `?` |
| 分离会话 | 前缀 + `d` |
| 关闭窗口 | 前缀 + `&` |
| 强制退出 | `Ctrl+Q` |

### 复制模式

详见 [复制模式](docs/copy_mode.md) 完整文档。

### 命令行

按 `Esc` 然后按 `:` 进入命令模式。

| 命令 | 说明 |
|------|------|
| `:exit` | 强制退出（清除所有保存状态） |
| `:split`, `:sp` | 水平分割 |
| `:vsplit`, `:vsp`, `:vs` | 垂直分割 |
| `:only` | 仅保留当前窗格 |
| `:focus <n>` | 按索引聚焦窗格 |
| `:theme <name>` | 切换主题 |
| `:theme list` | 打开主题浏览器 |
| `:layout` | 打开布局浏览器 |
| `:layout <name>` | 应用指定布局模板 |
| `:web [port]` | 启动 Web 客户端（默认端口 9888） |
| `:webstop` | 停止 Web 客户端服务器 |
| `:ls` | 打开会话浏览器 |
| `:plugins` | 打开插件管理器 |
| `:reload`, `:source` | 重新加载配置并加载新启用的插件 |
| `:help` | 显示帮助覆盖层 |

使用 `Tab` 进行命令补全。

## 热更新

plmux 自动监视配置文件的变化。当你编辑 `config.json` 时，更改会立即生效：

- **主题更改**立即生效
- **快捷键更改**在下次按键时生效
- **新启用的插件**自动加载
- **UI 设置**在下一帧生效

你也可以使用 `:reload` 或 `:source` 命令手动触发重载。

详见[配置 - 热更新](docs/configuration.zh-CN.md#热更新)了解哪些设置可以和不可以热更新。

## Web 客户端 (计划中)

plmux 内置 Web 服务器，支持通过浏览器访问终端。详见 [Web 客户端](docs/web-client.zh-CN.md) 完整文档。

```bash
:web              # 在默认端口 9888 启动
:web 8080         # 在自定义端口启动
:webstop          # 停止服务器
```

然后在浏览器中打开 `http://localhost:9888`。

## 配置

详见[配置](docs/configuration.zh-CN.md)完整文档。快捷键自定义详见[快捷键](docs/keybindings.zh-CN.md)。

## 主题

详见[主题](docs/themes.zh-CN.md)完整文档。

## 插件

详见[插件](docs/plugins.zh-CN.md)完整文档。

## 架构

plmux 在性能关键路径上使用 C 扩展：

- **FastScreen**（`plmux/terminal/_c_extension/`）：ANSI 解析、屏幕状态管理和渲染 — 不可用时回退到纯 Python pyte 后端
- **WebSocket 内核**（`plmux/web/_c_extension/`）：浏览器终端的帧解析和编码 — 不可用时回退到纯 Python WebSocket 实现

两个扩展均为可选；plmux 在没有它们的情况下也能正常工作，使用 Python 回退实现。

## 许可证

MIT

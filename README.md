# MoonTrace

**MoonTrace — A self-hosted media fetcher for Bilibili, YouTube, TikTok and more.**

> Trace. Fetch. Archive.

MoonTrace 是一个自托管媒体获取工具。目前 `v0.2` 已经完整支持 Bilibili，
并同时提供 Web UI 与 Telegram Bot。未来计划逐步加入 YouTube、TikTok 等平台。

## 当前版本：v0.2

已完成：

- Bilibili 链接 / BV 号解析
- 视频 MP4 下载
- M4A 音频
- 封面
- SRT 字幕
- 浏览器登录态 / Cookie
- 自定义保存目录
- 下载进度
- FFmpeg 合并
- Web UI
- Telegram Bot
- Telegram 用户白名单
- 一键启动脚本
- 多平台架构基础

## 项目结构

```text
MoonTrace/
├─ app.py
├─ config.py
├─ start.bat
├─ start_bot.bat
├─ start_all.bat
├─ setup.bat
├─ telegram_setup.bat
├─ requirements.txt
├─ .gitignore
├─ tools/
│  └─ ffmpeg/             # setup.bat 自动生成，不提交到仓库
│
├─ core/
│  ├─ platforms.py
│  ├─ parser.py
│  ├─ downloader.py
│  ├─ subtitles.py
│  ├─ thumbnail.py
│  ├─ cookies.py
│  └─ tasks.py
│
├─ web/
│  └─ routes.py
│
├─ telegram_bot/
│  ├─ bot.py
│  └─ configure.py
│
├─ static/
└─ downloads/
```

## 为什么新增 `core/platforms.py`

MoonTrace 不再把自己定义为“Bilibili 下载器”。

Web 与 Telegram 层只负责交互：

```text
Web / Telegram
      ↓
平台识别
      ↓
统一媒体解析
      ↓
下载核心
```

当前：

```text
Bilibili → 已启用
YouTube  → 计划加入
TikTok   → 计划加入
```

以后加入新平台时，应优先扩展平台检测与适配层，而不是复制一整套 Web / Telegram 逻辑。

## 启动

### Web

双击：

```text
start.bat
```

### Telegram Bot

双击：

```text
start_bot.bat
```

### Web + Telegram

双击：

```text
start_all.bat
```

## 首次安装 / 更新依赖

双击：

```text
setup.bat
```

安装脚本会自动完成：

- 检查 Python；
- 创建或复用 `.venv`；
- 安装 / 更新 `requirements.txt` 中的依赖；
- 检查 FFmpeg；
- 电脑中没有 FFmpeg 时，自动下载到 `tools/ffmpeg/bin/`。

已有 `.venv` 时不会删除现有环境。MoonTrace 会优先使用项目目录里的
FFmpeg，也兼容已经加入系统 `PATH` 的 FFmpeg。无需手动设置环境变量。

## Telegram 配置

双击：

```text
telegram_setup.bat
```

配置：

- Bot Token
- 允许使用 Bot 的 Telegram 用户 ID
- Telegram 上传安全阈值

敏感配置保存在：

```text
.env
```

`.env` 已加入 `.gitignore`，不要提交到 GitHub。

## Bilibili 登录态

MoonTrace 会继续复用网页设置中的浏览器登录态，例如：

```text
Chrome
Edge
Firefox
Brave
```

程序只保存浏览器/Profile 配置，不保存 Cookie 内容。

如果 Chrome 正在占用 Cookie 数据库而出现：

```text
Could not copy Chrome cookie database
```

请完全退出 Chrome 后重试，或改用其他浏览器登录态。

## Roadmap

```text
v0.1  Bilibili 核心下载功能
v0.2  Telegram Bot + MoonTrace 品牌重构
v0.3  YouTube
v0.4  TikTok
v0.5  多平台自动识别与统一格式
v1.0  正式多平台版本
```

## 项目名称

**MoonTrace**

> Trace. Fetch. Archive.


## v0.2.1

修复 Windows 项目目录改名或移动后，`activate.bat` 仍保存旧虚拟环境路径，
导致双击启动脚本没有正常启动的问题。

现在所有 BAT 均直接调用：

```text
.venv\Scripts\python.exe
```

不再依赖虚拟环境激活脚本，因此移动 `MoonTrace` 项目目录后更稳定。


## v0.2.2

Fixed Windows CMD parsing issues caused by UTF-8 / Chinese text in batch files.

All `.bat` launchers are now written as ASCII with Windows CRLF line endings.
This avoids mojibake and command corruption such as `cho`, `?echo`, or broken `if not exist`.


## v0.2.3 - Telegram 本地文件清理

Telegram Bot 在成功把下载结果上传到 Telegram 后，会询问：

```text
是否保留运行 MoonTrace 的电脑上的本地副本？

[💾 保留本地文件] [🗑 删除本地文件]
```

选择“删除本地文件”后还会出现一次确认，防止误删。

安全限制：

- 只有成功上传到 Telegram 后才会出现清理选项。
- 超过 Telegram 上传阈值、没有成功发送的文件不会自动询问删除。
- 删除回调只能操作对应 Telegram 下载任务生成的文件。
- 任务会记录 Telegram 用户 ID，其他用户无法通过回调删除该任务的文件。
- 删除本地副本不会影响 Telegram 中已经发送成功的文件。


## v0.2.4 - 竖屏画质与弹幕修复

### 画质显示

旧版本直接把视频的实际像素高度当成 `P`：

```text
996 × 1772 -> 1772P
498 × 886  -> 886P
```

对于竖屏视频会产生错误的人类可读画质名称。

v0.2.4 会优先读取 Bilibili / yt-dlp 的画质档位：

```text
1080P 60FPS
720P 60FPS
480P
360P
240P
```

同时 Web 界面仍会显示真实编码分辨率，例如：

```text
1080P
996×1772 · 60 FPS
```

下载选择仍使用真实格式尺寸，因此不会因为只改显示名称而选错流。

### 弹幕与字幕分离

yt-dlp 的 Bilibili extractor 会把：

```text
danmaku
```

作为 XML 轨放在 `subtitles` 数据中。

MoonTrace 现在会将它单独显示为：

```text
💬 弹幕 XML
```

真正的字幕（例如 `ai-zh`）则显示为：

```text
📝 AI 中文
```

Web 与 Telegram Bot 均已同步修复。


## v0.2.5 - MoonTrace Visual Refresh

Web UI visual redesign:

- Uses the supplied Type-Moon-style sky image as the full-page background.
- Adds a dark atmospheric overlay so text remains readable.
- Glassmorphism hero, settings, result, login, and task panels.
- Blue / violet MoonTrace accent gradient.
- Redesigned input, download buttons, quality selectors, progress bars and badges.
- Responsive mobile layout.
- `prefers-reduced-motion` support.
- Background image is stored locally at:

```text
static/images/moontrace-bg.jpg
```

No external image/CDN dependency is required.


## v0.2.6 - Background quality and scroll performance

- Replaced the compressed JPEG background with the user-supplied PNG image.
- Background is no longer blurred.
- Removed expensive live glass blur from the full page and large panels.
- Removed fixed-background scrolling mode that caused repaint stutter.
- Uses a dedicated fixed composited background layer instead.
- Reduced large shadow and repaint costs.
- Keeps the dark translucent MoonTrace visual style.

Background file:

```text
static/images/moontrace-bg.png
```


## v0.2.7 - Background visibility fix

Fixed a CSS stacking bug introduced in v0.2.6.

The background image layer used a negative z-index and was rendered behind the body's own background color, making the image invisible.

The fixed stack is now:

```text
background image layer  z-index: 0
dark readability overlay z-index: 0
MoonTrace content        z-index: 1
```

The overlay was also reduced slightly so the supplied PNG remains clearly visible.


## v0.2.8 - Moonlit Sigil

Added an original lunar / occult UI decoration layer while keeping the
existing high-performance background implementation.

Decorations include:

- MoonTrace lunar sigil
- geometric ring / circuit motifs
- card corner ornaments
- static star points
- thin “magic circuit” dividers
- serif section accents
- `REMOTE MEDIA TRACE SYSTEM` technical label
- `TRACE NETWORK / LOCAL ARCHIVE TERMINAL` footer label

All decorations are CSS / inline SVG and remain lightweight.
No real-time blur or large continuous animation was added.


## v0.2.9 - Quick Start

Added an in-page usage guide for first-time users.

The guide explains:

- how to parse Bilibili links / BV IDs
- how to choose video, audio, cover, subtitle and danmaku downloads
- why high-quality formats may be unavailable while logged out
- how to use a logged-in browser session with MoonTrace
- why a dedicated Firefox profile is a convenient option
- that Web and Telegram share the same MoonTrace settings
- that MoonTrace only uses permissions already available to the signed-in account

The guide uses native HTML `<details>` / `<summary>`, so it requires no extra JavaScript.


## v0.2.10 - Legal & Changelog

MoonTrace now includes:

- an in-page update log;
- an in-page Responsible Use / copyright boundary section;
- `CHANGELOG.md`;
- `LEGAL.md`;
- MIT `LICENSE`.

### Responsible use

MoonTrace is intended for personal archiving, research, and media that you own
or are authorized to access. Users are responsible for following applicable
copyright law and platform terms.

MoonTrace does not provide features intended to bypass DRM, paywalls,
membership restrictions, purchase checks, or other access controls.


## v0.2.11

- Rewrote the changelog in a more natural developer-log style.
- Final cleanup before the first public GitHub upload.

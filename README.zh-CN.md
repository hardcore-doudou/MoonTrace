# MoonTrace

[English](README.md) | **简体中文**

> **Follow the trace beyond the moon.**

MoonTrace 是一个自托管媒体获取工具。

目前主要支持 **Bilibili**，提供 Web UI 与 Telegram Bot 两种使用方式，并已经为后续加入 YouTube、TikTok 等平台预留了统一的平台适配层。

本地测试版本：**v0.3.0-beta.1**

桌面版试用与 Windows 打包说明见 [DESKTOP_TEST.md](DESKTOP_TEST.md)。原有 Web 与 Telegram 入口继续保留。

---

## 🚀 快速开始

MoonTrace 目前主要面向 **Windows**。

### 1. 下载 MoonTrace

如果不熟悉 Git，可以直接在 GitHub 项目页面点击：

```text
Code
→ Download ZIP
```

下载后解压即可。

如果使用 Git：

```powershell
git clone https://github.com/hardcore-doudou/MoonTrace.git
cd MoonTrace
```

### 2. 安装 Python

MoonTrace 需要：

```text
Python 3.10+
```

推荐使用 Python 3.13。

在 Windows 安装 Python 时，建议勾选 **Add Python to PATH**。

### 3. 首次安装

进入 MoonTrace 文件夹，双击：

```text
setup.bat
```

安装脚本会自动：

- 创建本地 Python 虚拟环境 `.venv`
- 安装项目所需 Python 依赖
- 检查 yt-dlp
- 检查 FFmpeg
- 如果电脑中没有可用的 FFmpeg，会自动下载一份到项目目录

正常情况下不需要手动安装 FFmpeg，也不需要自行配置环境变量。

### 4. 启动 MoonTrace

双击：

```text
start.bat
```

然后在浏览器打开：

```text
http://127.0.0.1:8000
```

基本使用流程：

```text
粘贴 Bilibili 链接 / BV 号
        ↓
解析
        ↓
选择画质 / 音频 / 封面 / 字幕 / 弹幕
        ↓
下载
```

### 5. 高画质需要登录时

先在支持的浏览器中登录 Bilibili，然后在 MoonTrace 中打开：

```text
下载设置
→ Bilibili 登录态
→ 选择浏览器
```

目前支持：

```text
Chrome
Edge
Firefox
Brave
```

MoonTrace 只会在本机复用浏览器登录状态，不会把你的 Bilibili 密码保存进项目配置。

### 可选：Telegram Bot

如果只使用网页，可以跳过这一部分。

首次配置 Telegram Bot 时运行：

```text
telegram_setup.bat
```

配置完成后启动：

```text
start_bot.bat
```

如果希望 Web 与 Telegram Bot 一起启动：

```text
start_all.bat
```

---

## 主题与本地自定义

MoonTrace 的公开仓库不再内置第三方角色立绘、游戏 CG 或其他受版权保护的背景图片。

默认界面使用 MoonTrace 自己的 CSS 月夜背景和原创界面装饰。

个人主题可以只保存在本机，不提交到 Git。创建：

```text
user_data/
└─ theme/
   ├─ background.png   # 也支持 .jpg / .jpeg / .webp
   └─ theme.css
```

只要放入名为 `background.png`、`background.jpg`、`background.jpeg` 或 `background.webp` 的图片，MoonTrace 就会自动把它作为网页背景。

`theme.css` 会在内置样式之后加载，因此可以自行覆盖配色、透明度、字体、卡片样式、装饰元素以及其他 CSS。

例如：

```css
:root {
  --accent-a: #75b8ff;
  --accent-b: #8572ff;
  --accent-c: #d18aff;
}

body::after {
  background: rgba(5, 10, 24, 0.36);
}
```

整个 `user_data/` 目录都已经加入 Git 忽略规则，因此个人背景和主题文件只留在本机，在更新或提交仓库时不会被上传。

可以从这个示例开始修改：

```text
themes/custom-theme.example.css
```

---

## 当前支持

### Bilibili

目前已经实现：

- Bilibili 视频链接 / BV 号解析
- 多画质 MP4 下载
- M4A 音频下载
- 视频封面下载
- SRT 字幕下载
- 弹幕 XML 下载
- 浏览器登录态读取
- 自定义保存目录
- 下载进度显示
- FFmpeg 音视频合并
- Web UI
- Telegram Bot
- Telegram 用户白名单
- Windows 一键安装与启动脚本

MoonTrace 目前只启用了 Bilibili 支持。

计划中的平台：

```text
抖音     → 计划加入
YouTube  → 计划加入
TikTok   → 计划加入
```

---

## v0.2.13

- Web 与 Telegram 的视频画质选择现在会传递 Bilibili `quality_id`，可区分相同分辨率下的 1080P、1080P+ 等不同画质档位。
- 修正 Bilibili 封面下载逻辑。
- 不再写死固定分辨率，也不再优先使用 `cover43` 这类 4:3 展示封面。
- 现在优先读取普通投稿封面的 `pic`，并去掉 CDN 的 `@...` 缩放 / 裁剪参数后下载。
- 按钮与文件名不再标注固定尺寸，尽量保留 B 站实际提供的封面尺寸。

## v0.2.12

这一版主要处理 FFmpeg 依赖。

`setup.bat` 现在会自动检查 FFmpeg：

```text
项目内 FFmpeg
      ↓
系统 PATH 中的 FFmpeg
      ↓
都没有
      ↓
自动下载 FFmpeg
```

如果电脑本身没有 FFmpeg，安装脚本会自动下载到：

```text
tools/ffmpeg/bin/
```

MoonTrace 会优先使用项目目录中的 FFmpeg，同时也兼容已经配置到系统 `PATH` 的 FFmpeg。

因此正常情况下不再需要用户手动安装 FFmpeg 或配置环境变量。

完整版本记录见：

[CHANGELOG.md](CHANGELOG.md)

---

## 项目结构

```text
MoonTrace/
├─ app.py
├─ config.py
├─ VERSION
│
├─ setup.bat
├─ start.bat
├─ start_bot.bat
├─ start_all.bat
├─ telegram_setup.bat
├─ requirements.txt
│
├─ core/
│  ├─ platforms.py
│  ├─ parser.py
│  ├─ downloader.py
│  ├─ subtitles.py
│  ├─ thumbnail.py
│  ├─ cookies.py
│  ├─ ffmpeg.py
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
│  ├─ index.html
│  ├─ style.css
│  ├─ app.js
│  ├─ favicon.svg
│  └─ images/
│
├─ downloads/
│
└─ tools/
   └─ ffmpeg/        # setup.bat 自动生成，不提交到 Git
```

---

## 安装

MoonTrace 目前主要面向 Windows。

建议使用：

```text
Python 3.10+
```

项目开发环境主要使用 Python 3.13。

下载或 Clone 项目后，运行：

```text
setup.bat
```

安装脚本会自动：

1. 检查 Python
2. 创建或复用 `.venv`
3. 安装 `requirements.txt` 中的 Python 依赖
4. 检查 yt-dlp
5. 检查 FFmpeg
6. 必要时自动下载项目本地 FFmpeg

已有 `.venv` 时不会自动删除原有虚拟环境。

---

## 启动 Web

双击：

```text
start.bat
```

然后打开：

```text
http://127.0.0.1:8000
```

MoonTrace Web 可以直接完成：

```text
粘贴链接
    ↓
解析视频
    ↓
选择画质 / 音频 / 封面 / 字幕 / 弹幕
    ↓
下载
```

---

## Telegram Bot

MoonTrace 同时提供 Telegram Bot。

首次使用前运行：

```text
telegram_setup.bat
```

需要配置：

- Telegram Bot Token
- 允许使用下载功能的 Telegram 用户 ID
- Telegram 文件上传大小阈值

配置完成后运行：

```text
start_bot.bat
```

如果希望同时启动 Web 与 Telegram Bot：

```text
start_all.bat
```

Telegram Bot 支持：

- 发送 Bilibili 链接后自动解析
- 选择视频画质
- 下载 M4A 音频
- 下载封面
- 下载字幕
- 下载弹幕 XML
- 下载完成后发送到 Telegram
- 文件发送成功后选择是否删除电脑中的本地副本

---

## Telegram 配置文件

Telegram 配置保存在：

```text
.env
```

例如：

```env
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_USERS=
TELEGRAM_MAX_UPLOAD_MB=49
```

`.env` 已加入 `.gitignore`。

**不要把自己的 Bot Token 提交到 GitHub。**

---

## Bilibili 登录态

部分 Bilibili 画质或内容需要登录后才能正常读取。

MoonTrace 可以直接复用本机浏览器现有的登录状态，目前支持：

```text
Chrome
Edge
Firefox
Brave
```

可以在 Web 页面中的：

```text
下载设置
→ Bilibili 登录态
```

选择浏览器。

MoonTrace 保存的只是：

```text
浏览器类型
Profile 配置
```

不会把 Bilibili 密码保存进项目配置文件，也不会把浏览器 Cookie 内容导出到 `settings.json`。

### Chrome / Edge Cookie 读取失败

如果出现类似：

```text
Could not copy Chrome cookie database
```

通常是因为 Chrome 或 Edge 正在占用 Cookie 数据库。

可以：

```text
完全退出浏览器后重新尝试
```

或者单独准备一个 Firefox 用于 MoonTrace。

---

## 画质

MoonTrace 会尽量使用 Bilibili / yt-dlp 提供的实际画质档位，而不是简单地把视频像素高度当作画质名称。

例如竖屏视频：

```text
996 × 1772
```

不会再错误显示成：

```text
1772P
```

而会优先显示类似：

```text
1080P
996×1772 · 60 FPS
```

实际下载仍然按照真实媒体格式选择。

---

## 字幕与弹幕

Bilibili 的弹幕和字幕在底层数据中可能同时出现在 subtitle 信息里。

MoonTrace 会把两者分开处理：

```text
字幕
├─ AI 中文
├─ 简体中文
├─ English
└─ ...

弹幕
└─ XML
```

字幕可以保存为：

```text
.srt
```

弹幕保存为：

```text
.xml
```

---

## 多平台架构

MoonTrace 不希望长期只是一个写死 Bilibili 逻辑的下载器。

目前的基本结构是：

```text
Web / Telegram
      ↓
平台识别
      ↓
统一媒体解析
      ↓
下载核心
```

平台检测集中在：

```text
core/platforms.py
```

因此以后增加新平台时，目标是继续扩展平台识别与适配层，而不是分别复制一整套 Web 和 Telegram 下载逻辑。

---

## 保存目录

默认下载目录：

```text
downloads/
```

Web UI 中可以修改默认保存位置，也可以启用：

```text
每次下载前询问保存位置
```

本地设置保存在：

```text
settings.json
```

该文件已经加入 `.gitignore`，不会提交到 GitHub。

---

## Roadmap

```text
v0.1
Bilibili 核心下载功能

v0.2
Telegram Bot
MoonTrace 品牌重构
Web UI 改进
字幕 / 弹幕
浏览器登录态
FFmpeg 自动处理

v0.3
YouTube

v0.4
TikTok

v0.5
多平台自动识别与统一格式

v1.0
正式多平台版本
```

Roadmap 只是目前的开发方向，具体版本安排可能会随着开发过程调整。

---

## 使用边界

MoonTrace 主要用于：

- 保存自己上传或制作的内容
- 保存已经获得授权的内容
- 个人归档与研究
- 其他你有权访问和使用的媒体

MoonTrace 只使用当前用户或账号已经拥有的访问权限。

项目不提供用于绕过以下限制的功能：

```text
DRM
付费墙
会员权限
购买验证
其他访问控制
```

下载内容也不代表自动获得重新上传、传播或商业使用的权利。

使用 MoonTrace 时，请自行遵守所在地法律、著作权规则以及对应平台的服务条款。

更完整的说明见：

[LEGAL.md](LEGAL.md)

---

## 隐私与本地运行

MoonTrace 是一个自托管项目。

Web 服务默认运行在：

```text
127.0.0.1:8000
```

下载文件默认保存在本机。

项目不会要求把 Bilibili 密码提交到 MoonTrace，也不会把 `.env`、`settings.json` 或浏览器 Cookie 内容上传到仓库。

---

## 开发状态

MoonTrace 目前仍处于早期开发阶段。

可能仍然存在：

- 特殊视频解析异常
- Bilibili API / yt-dlp 更新导致兼容性变化
- 特殊画质格式选择问题
- Telegram 文件大小限制
- Windows 环境差异导致的启动问题

如果遇到问题，可以在 GitHub Issues 中提交复现信息。

---

## License

MoonTrace 使用 MIT License。

详见：

[LICENSE](LICENSE)

---

## MoonTrace

> **Follow the trace beyond the moon.**

当前版本：

```text
v0.2.13
```

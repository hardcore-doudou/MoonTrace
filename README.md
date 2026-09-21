# MoonTrace

**English** | [简体中文](README.zh-CN.md)

> **Follow the trace beyond the moon.**

MoonTrace is a self-hosted media fetching tool.

It currently focuses on **Bilibili** and provides both a Web UI and a Telegram Bot. A unified platform adapter layer is already in place for future support of platforms such as YouTube, TikTok, and Douyin.

Current version: **v0.2.14**

---

## Current Support

### Bilibili

Currently implemented:

- Bilibili video URL / BV ID parsing
- Multi-quality MP4 downloads
- M4A audio downloads
- Video thumbnail downloads
- SRT subtitle downloads
- Danmaku XML downloads
- Browser session / cookie support
- Custom download directories
- Download progress display
- FFmpeg audio/video merging
- Web UI
- Telegram Bot
- Telegram user whitelist
- One-click Windows setup and launch scripts

MoonTrace currently has Bilibili support enabled.

Planned platforms:

```text
Douyin   → Planned
YouTube  → Planned
TikTok   → Planned
```

---

## v0.2.14

This release changes Bilibili cover retrieval to prefer the official video-info API.

- Read the submission cover from `data.pic` returned by Bilibili's video-info endpoint.
- Remove CDN `@...` resize/crop suffixes before downloading when present.
- Fall back to yt-dlp thumbnail metadata only when the official endpoint is unavailable.

## v0.2.13

This release improves Bilibili thumbnail handling.

- Prefer the largest thumbnail candidate reported by yt-dlp.
- Remove Bilibili CDN `@...` resize/crop suffixes when possible to request the original image.
- Fall back to the original yt-dlp thumbnail URL if the source image cannot be fetched.

## v0.2.12

This release mainly focuses on FFmpeg dependency handling.

`setup.bat` now automatically checks for FFmpeg:

```text
Project-local FFmpeg
        ↓
FFmpeg in system PATH
        ↓
Neither found
        ↓
Automatically download FFmpeg
```

If FFmpeg is not already installed on the system, the setup script will automatically download it to:

```text
tools/ffmpeg/bin/
```

MoonTrace prefers the project-local FFmpeg installation while remaining compatible with FFmpeg already available through the system `PATH`.

In normal use, users no longer need to manually install FFmpeg or configure environment variables.

For the full version history, see:

[CHANGELOG.md](CHANGELOG.md)

---

## Project Structure

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
   └─ ffmpeg/        # Generated automatically by setup.bat; not committed to Git
```

---

## Installation

MoonTrace is currently designed primarily for Windows.

Recommended:

```text
Python 3.10+
```

The project is mainly developed and tested with Python 3.13.

After downloading or cloning the project, run:

```text
setup.bat
```

The setup script will automatically:

1. Check for Python
2. Create or reuse `.venv`
3. Install Python dependencies from `requirements.txt`
4. Verify yt-dlp
5. Check for FFmpeg
6. Download a project-local FFmpeg installation when necessary

If `.venv` already exists, the existing virtual environment will not be deleted automatically.

---

## Starting the Web UI

Double-click:

```text
start.bat
```

Then open:

```text
http://127.0.0.1:8000
```

MoonTrace Web provides the following basic workflow:

```text
Paste a URL
    ↓
Parse media
    ↓
Choose video quality / audio / thumbnail / subtitles / danmaku
    ↓
Download
```

---

## Telegram Bot

MoonTrace also includes a Telegram Bot.

Before using it for the first time, run:

```text
telegram_setup.bat
```

You will need to configure:

- Telegram Bot Token
- Telegram user IDs allowed to use download features
- Telegram file upload size threshold

After configuration, run:

```text
start_bot.bat
```

To start both the Web UI and Telegram Bot:

```text
start_all.bat
```

The Telegram Bot supports:

- Automatic parsing after sending a Bilibili URL
- Video quality selection
- M4A audio downloads
- Thumbnail downloads
- Subtitle downloads
- Danmaku XML downloads
- Sending completed downloads to Telegram
- Choosing whether to keep or delete the local copy after a file is successfully sent

---

## Telegram Configuration

Telegram configuration is stored in:

```text
.env
```

For example:

```env
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_USERS=
TELEGRAM_MAX_UPLOAD_MB=49
```

`.env` is already included in `.gitignore`.

**Never commit your Bot Token to GitHub.**

---

## Bilibili Login Session

Some Bilibili content or higher-quality formats may require a logged-in account.

MoonTrace can reuse an existing login session from a local browser.

Currently supported browsers:

```text
Chrome
Edge
Firefox
Brave
```

You can select the browser from:

```text
Download Settings
→ Bilibili Login Session
```

MoonTrace only stores:

```text
Browser type
Profile configuration
```

It does not save your Bilibili password in the project configuration, nor does it export browser cookie contents into `settings.json`.

### Chrome / Edge Cookie Read Errors

If you see an error such as:

```text
Could not copy Chrome cookie database
```

Chrome or Edge is usually still using and locking the cookie database.

Try:

```text
Completely close the browser and try again
```

Alternatively, you can use a dedicated Firefox profile for MoonTrace.

---

## Video Quality

MoonTrace tries to use the actual quality levels provided by Bilibili / yt-dlp instead of simply treating the pixel height as the quality label.

For example, a vertical video with a resolution of:

```text
996 × 1772
```

will no longer be incorrectly shown as:

```text
1772P
```

Instead, MoonTrace will prefer a label such as:

```text
1080P
996×1772 · 60 FPS
```

The actual media format and resolution are still used when selecting the download stream.

---

## Subtitles and Danmaku

Bilibili subtitles and danmaku may both appear under subtitle-related metadata at the extractor level.

MoonTrace handles them separately:

```text
Subtitles
├─ AI Chinese
├─ Simplified Chinese
├─ English
└─ ...

Danmaku
└─ XML
```

Subtitles can be saved as:

```text
.srt
```

Danmaku is saved as:

```text
.xml
```

---

## Multi-Platform Architecture

MoonTrace is not intended to remain a downloader with Bilibili-specific logic hard-coded everywhere.

The current basic architecture is:

```text
Web / Telegram
      ↓
Platform detection
      ↓
Unified media parsing
      ↓
Download core
```

Platform detection is centralized in:

```text
core/platforms.py
```

When new platforms are added, the goal is to extend the platform detection and adapter layer instead of duplicating an entire Web and Telegram download implementation for each platform.

---

## Download Directory

The default download directory is:

```text
downloads/
```

The default save location can be changed from the Web UI.

You can also enable:

```text
Ask for a save location before each download
```

Local settings are stored in:

```text
settings.json
```

This file is already included in `.gitignore` and will not be committed to GitHub.

---

## Roadmap

```text
v0.1
Core Bilibili download features

v0.2
Telegram Bot
MoonTrace rebranding
Web UI improvements
Subtitles / danmaku
Browser login sessions
Automatic FFmpeg handling

v0.3
YouTube

v0.4
TikTok

v0.5
Automatic multi-platform detection and unified formats

v1.0
Full multi-platform release
```

The roadmap reflects the current development direction and may change as the project evolves.

---

## Responsible Use

MoonTrace is primarily intended for:

- Saving content you created or uploaded yourself
- Saving content you have permission to download
- Personal archiving and research
- Other media you are authorized to access and use

MoonTrace only uses access permissions already available to the current user or account.

The project does not provide features intended to bypass:

```text
DRM
Paywalls
Membership restrictions
Purchase verification
Other access controls
```

Downloading content does not automatically grant permission to re-upload, redistribute, or use it commercially.

When using MoonTrace, you are responsible for complying with applicable laws, copyright rules, and the terms of service of the relevant platforms.

For more details, see:

[LEGAL.md](LEGAL.md)

---

## Privacy and Local Operation

MoonTrace is a self-hosted project.

By default, the Web service runs on:

```text
127.0.0.1:8000
```

Downloaded files are stored locally.

MoonTrace does not require you to submit your Bilibili password to the project, and it does not upload `.env`, `settings.json`, or browser cookie contents to the repository.

---

## Development Status

MoonTrace is still in an early stage of development.

There may still be issues involving:

- Parsing certain unusual videos
- Compatibility changes caused by Bilibili API or yt-dlp updates
- Format selection for unusual video qualities
- Telegram file size limits
- Startup issues caused by differences between Windows environments

If you encounter a problem, feel free to open a GitHub Issue with enough information to reproduce it.

---

## License

MoonTrace is licensed under the MIT License.

See:

[LICENSE](LICENSE)

---

## MoonTrace

> **Follow the trace beyond the moon.**

Current version:

```text
v0.2.14
```

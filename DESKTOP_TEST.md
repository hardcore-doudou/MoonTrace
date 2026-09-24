# MoonTrace 桌面测试版（v0.3.0-beta.1）

这份 ZIP 是 **v0.3.0-beta.1 预发布版的源代码测试包**，不是已编译的 Windows EXE 或安装程序。

## 在 Windows 11 本地试用

1. 解压 ZIP。已有 MoonTrace 用户请先备份原目录；覆盖时保留自己的 `.env`、`settings.json`、`user_data/`、`downloads/`。
2. 首次运行 `setup.bat`，安装 Python 依赖并检查 FFmpeg。
3. 双击 `start_desktop.bat`。脚本首次运行会安装桌面窗口依赖，然后打开 MoonTrace 独立窗口。
4. 在「设置 → 外观与主题」更换配色、背景图和暗度；在「下载」查看共用的任务记录。

原有 `start.bat`、`start_bot.bat` 和 `start_all.bat` 仍可按原方式使用。源代码方式运行时，SQLite 与私人主题继续保存在项目目录 `user_data/`，现有 `.env` 和 `settings.json` 路径不变。主题图仅接受小于 12 MB 的 PNG、JPEG、WebP。

**关闭桌面窗口会停止该窗口内启动的下载服务。** 当前下载完成后再关闭；下一次启动时中断的任务会标为失败，可在下载页重试。桌面托盘与下载中关闭窗口的处理仍待下一阶段完善。

## 在 Windows 上生成免安装版

运行 `build_windows.bat`，它会生成 `dist\MoonTrace\MoonTrace.exe` 和 `dist\MoonTrace-<VERSION>-Windows-Portable.zip`。图标暂用默认图标。ZIP 内含程序、FFmpeg 和便携标记，解压整个文件夹即可使用，不需另行安装 Python。生成前须安装 Python、桌面依赖以及 FFmpeg；脚本会检查并打包 FFmpeg 工具。Windows 可能需要 WebView2 Runtime。**尚未在 Windows 构建和验证**，不要把源代码测试 ZIP 当成可直接运行的 EXE。

便携版的 SQLite 历史、下载目录、设置文件和背景图位于 EXE 旁的 `MoonTraceData\`。更新时保留整个 `MoonTraceData\` 文件夹；从源代码版迁移时，可在退出程序后手动复制 `user_data/`、`downloads/` 及自己的 `settings.json` 到该目录；原文件不会被自动修改。若旧设置记录了原目录的下载路径，该路径仍需要存在。

需要让**源码版 Telegram Bot 与便携桌面版共用 SQLite** 时，在原项目目录运行 `start_bot_desktop.bat "D:\\你的目录\\MoonTrace\\MoonTraceData"`，传入便携版数据目录的绝对路径。Bot 仍可读取原项目里的 `.env`，不会修改该文件。此构建脚本只生成桌面窗口程序。

Windows 验收：解压 ZIP，在没有 Python 的机器上双击 `MoonTrace.exe`；解析并下载一条 Bilibili 视频，确认 `MoonTraceData\downloads` 有文件；退出重启确认任务历史仍在；检查主题设置、打开文件和文件夹；在原项目启动 Web 与 Telegram，确认两者没有回归。发布 EXE 前须完成此验收。

仓库源代码与将来的 Release 文件均不能包含 `.env`、个人 `settings.json`、Cookie、`user_data/`、下载文件及构建缓存。发布前需在 Windows 上完成实际下载、重启留存及 Web／Telegram 回归测试。

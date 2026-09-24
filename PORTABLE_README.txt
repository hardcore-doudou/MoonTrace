MoonTrace Windows 便携版

1. 解压整个 MoonTrace 文件夹，双击 MoonTrace.exe。
2. 首次启动会在 MoonTrace.exe 旁创建 MoonTraceData 文件夹。
   下载文件、任务历史、主题和设置均保存在该文件夹中。
3. 更新时先退出 MoonTrace，只替换程序文件夹中的文件，保留
   MoonTraceData 文件夹。迁移电脑时复制整个 MoonTrace 文件夹。
4. 从旧版迁移：退出程序后，将旧版的 user_data 文件夹、settings.json
   和 downloads 文件夹复制到 MoonTraceData。请勿把私人配置上传到 GitHub。
5. Telegram Bot 仍需要单独的 Python 运行环境。若要与便携桌面版共用
   任务历史，在启动 Bot 前将 MOONTRACE_DATA_DIR 设为 MoonTraceData 的
   完整路径；Bot 的 .env 仍留在原项目目录。

需要 Windows WebView2 Runtime。如系统无法加载 .NET 视窗组件，程序会
自动使用 Microsoft Edge 独立应用窗口（需系统安装 Edge）。
关闭桌面窗口时，进行中的下载会中断；
重启后可在下载页重新尝试失败的任务。

from __future__ import annotations

import asyncio
import os
import re
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest, NetworkError, TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import BASE_DIR, load_settings, resolve_output_dir, settings_lock
from core.downloader import download_worker
from core.ffmpeg import find_ffmpeg
from core.parser import (
    extract_media_info,
    get_available_qualities,
    get_subtitle_languages,
    has_danmaku,
    normalize_media_url,
)
from core.platforms import detect_platform
from core.tasks import create_task, get_task, update_task


ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE)

TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()

MAX_UPLOAD_MB = float(os.getenv("TELEGRAM_MAX_UPLOAD_MB") or "49")
MAX_UPLOAD_BYTES = int(MAX_UPLOAD_MB * 1024 * 1024)

# 下载任务同时最多跑 2 个，避免家里的机器一下被很多任务塞满。
DOWNLOAD_SEMAPHORE = asyncio.Semaphore(2)

# 解析后的临时会话：session_id -> data
SESSIONS: dict[str, dict] = {}

# 会话保留 6 小时，避免长期占内存。
SESSION_TTL = 6 * 60 * 60


def parse_allowed_users() -> set[int]:
    raw = (os.getenv("TELEGRAM_ALLOWED_USERS") or "").strip()
    if not raw:
        return set()

    result = set()

    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue

        try:
            result.add(int(item))
        except ValueError:
            pass

    return result


ALLOWED_USERS = parse_allowed_users()


def is_authorized(user_id: int | None) -> bool:
    if user_id is None:
        return False

    # 没配置允许用户时，默认不开放下载功能。
    return user_id in ALLOWED_USERS


def cleanup_sessions() -> None:
    now = time.time()
    expired = [
        sid
        for sid, data in SESSIONS.items()
        if now - data.get("created_at", now) > SESSION_TTL
    ]

    for sid in expired:
        SESSIONS.pop(sid, None)


def format_duration(seconds) -> str:
    if seconds is None:
        return "未知"

    total = int(seconds)
    hours, remain = divmod(total, 3600)
    minutes, secs = divmod(remain, 60)

    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"

    return f"{minutes}:{secs:02d}"


def format_bytes(value: int | float | None) -> str:
    if value is None:
        return ""

    value = float(value)
    units = ["B", "KB", "MB", "GB"]
    index = 0

    while value >= 1024 and index < len(units) - 1:
        value /= 1024
        index += 1

    if index == 0:
        return f"{value:.0f} {units[index]}"

    return f"{value:.1f} {units[index]}"


def component_progress(component: dict | None) -> str:
    if not component:
        return "等待"

    if component.get("status") == "done":
        return "100% ✓"

    progress = component.get("progress")
    speed = component.get("speed")
    eta = component.get("eta")

    parts = []

    if isinstance(progress, (int, float)):
        parts.append(f"{progress:.1f}%")
    else:
        parts.append("下载中")

    if speed:
        parts.append(f"{format_bytes(speed)}/s")

    if eta is not None:
        parts.append(f"剩余约 {eta}s")

    return " · ".join(parts)


def task_text(task: dict) -> str:
    status = task.get("status")
    kind = task.get("kind")

    names = {
        "video": "视频",
        "audio": "音频",
        "cover": "封面",
        "subtitle": "字幕",
        "danmaku": "弹幕",
    }

    title = names.get(kind, "下载任务")

    if status in ("queued", "starting"):
        return f"⏳ {title}：准备中…"

    if status == "processing":
        if kind == "video":
            return (
                f"⚙️ {title}：下载阶段完成\n"
                "正在由 FFmpeg 合并音视频…"
            )

        return f"⚙️ {title}：处理中…"

    if status == "downloading":
        components = task.get("components") or {}

        if kind == "video":
            return (
                f"⬇️ {title}下载中\n\n"
                f"🎞 视频：{component_progress(components.get('video'))}\n"
                f"🎵 音频：{component_progress(components.get('audio'))}"
            )

        component = (
            components.get("audio")
            or components.get("file")
            or components.get("video")
        )

        return (
            f"⬇️ {title}下载中\n\n"
            f"{component_progress(component)}"
        )

    if status == "error":
        return (
            f"❌ {title}失败\n\n"
            f"{task.get('error') or '未知错误'}"
        )

    if status == "done":
        size = format_bytes(task.get("file_size"))
        size_text = f"\n大小：{size}" if size else ""

        return (
            f"✅ {title}完成\n\n"
            f"文件：{task.get('filename')}"
            f"{size_text}"
        )

    return f"{title}：{status}"


def create_session(url: str, info: dict) -> str:
    cleanup_sessions()

    session_id = uuid.uuid4().hex[:10]

    SESSIONS[session_id] = {
        "created_at": time.time(),
        "url": url,
        "info": info,
        "qualities": get_available_qualities(info),
        "subtitles": get_subtitle_languages(info),
        "danmaku": has_danmaku(info),
    }

    return session_id


def get_session(session_id: str) -> dict | None:
    cleanup_sessions()
    return SESSIONS.get(session_id)


def build_media_keyboard(session_id: str, session: dict) -> InlineKeyboardMarkup:
    rows = []
    qualities = session.get("qualities") or []

    # 每行最多两个画质按钮。
    quality_row = []

    for quality in qualities:
        height = int(quality["height"])
        label = str(quality.get("label") or f"{height}P")

        fps = quality.get("fps")
        if fps and fps > 30:
            label += f" {int(round(fps))}FPS"

        quality_row.append(
            InlineKeyboardButton(
                label,
                callback_data=f"v:{session_id}:{height}",
            )
        )

        if len(quality_row) == 2:
            rows.append(quality_row)
            quality_row = []

    if quality_row:
        rows.append(quality_row)

    rows.append([
        InlineKeyboardButton(
            "🎵 仅音频 M4A",
            callback_data=f"a:{session_id}",
        ),
        InlineKeyboardButton(
            "🖼 封面",
            callback_data=f"c:{session_id}",
        ),
    ])

    subtitles = session.get("subtitles") or []

    # 避免一个消息出现过多按钮，最多先显示 8 个字幕轨。
    for index, subtitle in enumerate(subtitles[:8]):
        label = str(subtitle.get("name") or subtitle.get("id") or "字幕")

        if len(label) > 24:
            label = label[:23] + "…"

        rows.append([
            InlineKeyboardButton(
                f"📝 {label}",
                callback_data=f"s:{session_id}:{index}",
            )
        ])

    if session.get("danmaku"):
        rows.append([
            InlineKeyboardButton(
                "💬 弹幕 XML",
                callback_data=f"d:{session_id}",
            )
        ])

    rows.append([
        InlineKeyboardButton(
            "🔗 打开原视频",
            url=session["url"],
        )
    ])

    return InlineKeyboardMarkup(rows)


async def command_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    user = update.effective_user

    if not user:
        return

    if not is_authorized(user.id):
        await update.effective_message.reply_text(
            "👋 MoonTrace Bot 已启动。\n\n"
            "目前这个 Bot 还没有授权你的 Telegram 用户 ID。\n"
            "请发送 /whoami 查看你的数字 ID，然后把它写入项目的 "
            "TELEGRAM_ALLOWED_USERS。"
        )
        return

    await update.effective_message.reply_text(
        "👋 MoonTrace 已上线。\n\n"
        "直接把 Bilibili 链接或 BV 号发给我即可。\n\n"
        "支持：\n"
        "• 视频 MP4\n"
        "• M4A 音频\n"
        "• 封面\n"
        "• SRT 字幕\n"
        "• Bilibili 弹幕 XML\n\n"
        "使用 /status 查看服务器状态。"
    )


async def command_help(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    await update.effective_message.reply_text(
        "MoonTrace Bot\n\n"
        "/start - 使用说明\n"
        "/whoami - 查看你的 Telegram 用户 ID\n"
        "/status - 查看下载服务器状态\n\n"
        "发送一个 BV 号或 Bilibili 链接即可开始解析。"
    )


async def command_whoami(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    user = update.effective_user

    if not user:
        return

    await update.effective_message.reply_text(
        f"你的 Telegram 用户 ID：\n\n`{user.id}`",
        parse_mode=ParseMode.MARKDOWN,
    )


async def command_status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    user = update.effective_user

    if not user or not is_authorized(user.id):
        await update.effective_message.reply_text(
            "未授权。先发送 /whoami 获取你的用户 ID。"
        )
        return

    with settings_lock:
        settings = load_settings()

    ffmpeg = find_ffmpeg()

    await update.effective_message.reply_text(
        "🖥 MoonTrace Server\n\n"
        f"FFmpeg：{'✅ ' + str(ffmpeg) if ffmpeg else '❌ 未找到，请运行 setup.bat'}\n"
        f"媒体登录态来源：{settings.get('cookie_browser', 'none')}\n"
        f"分片并发：{settings.get('concurrent_fragments', 4)}\n"
        f"保存目录：\n{settings.get('download_dir')}"
    )


async def handle_link(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    user = update.effective_user
    message = update.effective_message

    if not user or not message or not message.text:
        return

    if not is_authorized(user.id):
        await message.reply_text(
            "这个 Bot 当前不允许未授权用户执行下载。\n"
            "发送 /whoami 获取你的用户 ID。"
        )
        return

    raw = message.text.strip()

    # 防止普通聊天文本触发一大串 yt-dlp 错误。
    looks_like_bili = (
        raw.upper().startswith("BV")
        or "bilibili.com" in raw.lower()
        or "b23.tv" in raw.lower()
    )

    if not looks_like_bili:
        await message.reply_text(
            "请发送 Bilibili 链接、b23.tv 链接或 BV 号。"
        )
        return

    status = await message.reply_text("🔎 正在解析 Bilibili 视频…")

    try:
        url = normalize_media_url(raw)
        info = await asyncio.to_thread(extract_media_info, url)

        # 优先使用 yt-dlp 解析后的 canonical URL。
        canonical_url = info.get("webpage_url") or url
        session_id = create_session(canonical_url, info)
        session = get_session(session_id)

        title = info.get("title") or "未知标题"
        uploader = (
            info.get("uploader")
            or info.get("channel")
            or "未知作者"
        )
        duration = format_duration(info.get("duration"))
        platform = detect_platform(canonical_url)

        qualities = session.get("qualities") or []
        subtitles = session.get("subtitles") or []

        text = (
            f"{platform.emoji} {platform.display_name}\n"
            f"🎬 {title}\n\n"
            f"作者：{uploader}\n"
            f"时长：{duration}\n"
            f"画质：{len(qualities)} 个\n"
            f"字幕：{len(subtitles)} 个\n"
            f"弹幕：{'有' if session.get('danmaku') else '无'}\n\n"
            "请选择："
        )

        await status.edit_text(
            text,
            reply_markup=build_media_keyboard(session_id, session),
        )

    except Exception as exc:
        await status.edit_text(
            f"❌ 解析失败\n\n{exc}"
        )


async def edit_progress_safely(message, text: str) -> None:
    try:
        await message.edit_text(text)
    except BadRequest as exc:
        # 文本完全一样时 Telegram 会抛 "Message is not modified"。
        if "not modified" not in str(exc).lower():
            raise



def build_local_file_choice_keyboard(task_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💾 保留本地文件",
                callback_data=f"filekeep:{task_id}",
            ),
            InlineKeyboardButton(
                "🗑 删除本地文件",
                callback_data=f"filedelete:{task_id}",
            ),
        ]
    ])


def build_delete_confirm_keyboard(task_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "⚠️ 确认删除",
                callback_data=f"filedeleteconfirm:{task_id}",
            ),
            InlineKeyboardButton(
                "取消",
                callback_data=f"filekeep:{task_id}",
            ),
        ]
    ])


def get_owned_telegram_task(task_id: str, user_id: int) -> dict | None:
    task = get_task(task_id)

    if not task:
        return None

    if task.get("source") != "telegram":
        return None

    if task.get("telegram_owner_user_id") != user_id:
        return None

    return task


async def handle_local_file_action(query, user_id: int, data: str) -> bool:
    """
    Handle callbacks related to local-file cleanup.

    Returns True when the callback was a file action, so the normal media
    callback router should stop processing it.
    """
    if ":" not in data:
        return False

    action, task_id = data.split(":", 1)

    if action not in {
        "filekeep",
        "filedelete",
        "filedeleteconfirm",
    }:
        return False

    task = get_owned_telegram_task(task_id, user_id)

    if not task:
        await query.edit_message_text(
            "这个文件任务不存在、已经过期，或不属于当前用户。"
        )
        return True

    filename = task.get("filename") or "文件"
    filepath = task.get("filepath")

    if action == "filekeep":
        if task.get("local_deleted"):
            await query.edit_message_text(
                f"🗑 本地文件已经删除：\n{filename}"
            )
        else:
            await query.edit_message_text(
                f"💾 已保留电脑上的本地文件：\n{filename}"
            )
        return True

    if action == "filedelete":
        if task.get("local_deleted") or not filepath:
            await query.edit_message_text(
                f"🗑 本地文件已经删除：\n{filename}"
            )
            return True

        await query.edit_message_text(
            "⚠️ 确认从运行 MoonTrace 的电脑上删除这个文件？\n\n"
            f"{filename}\n\n"
            "Telegram 里已经发送成功的文件不会受到影响。",
            reply_markup=build_delete_confirm_keyboard(task_id),
        )
        return True

    # filedeleteconfirm
    if task.get("local_deleted") or not filepath:
        await query.edit_message_text(
            f"🗑 本地文件已经删除：\n{filename}"
        )
        return True

    path = Path(filepath)

    try:
        if path.exists():
            if not path.is_file():
                raise RuntimeError("目标不是普通文件")
            path.unlink()

        update_task(
            task_id,
            local_deleted=True,
            filepath=None,
            file_size=0,
        )

        await query.edit_message_text(
            "🗑 已删除电脑上的本地文件。\n\n"
            f"{filename}\n\n"
            "Telegram 中已发送的副本仍然保留。"
        )

    except Exception as exc:
        await query.edit_message_text(
            "❌ 删除本地文件失败。\n\n"
            f"{exc}"
        )

    return True


async def send_finished_file(
    query,
    task_id: str,
    task: dict,
) -> None:
    filepath = task.get("filepath")

    if not filepath:
        await query.message.reply_text("文件路径不存在。")
        return

    path = Path(filepath)

    if not path.exists():
        await query.message.reply_text("文件已经不存在于服务器。")
        return

    size = path.stat().st_size

    if size > MAX_UPLOAD_BYTES:
        await query.message.reply_text(
            "📦 文件已经下载到家里的电脑，但超过当前标准 Telegram Bot API "
            f"上传限制（本项目安全阈值 {MAX_UPLOAD_MB:g} MB）。\n\n"
            f"文件：{path.name}\n"
            f"大小：{format_bytes(size)}\n"
            f"保存位置：{path}\n\n"
            "后续可以接入 Local Bot API Server 来处理更大的 Telegram 上传。"
        )
        return

    await query.message.reply_text(
        f"📤 正在上传到 Telegram：{path.name}"
    )

    try:
        with path.open("rb") as file_obj:
            await query.message.reply_document(
                document=file_obj,
                filename=path.name,
                read_timeout=180,
                write_timeout=180,
                connect_timeout=60,
                pool_timeout=60,
            )

        await query.message.reply_text(
            "✅ 文件已经成功发送到 Telegram。\n\n"
            "是否保留运行 MoonTrace 的电脑上的本地副本？",
            reply_markup=build_local_file_choice_keyboard(task_id),
        )

    except TelegramError as exc:
        await query.message.reply_text(
            "文件已保存在家里电脑，但上传 Telegram 失败：\n"
            f"{exc}"
        )


async def run_download_from_callback(
    query,
    session: dict,
    kind: str,
    height: int | None = None,
    subtitle_lang: str | None = None,
) -> None:
    async with DOWNLOAD_SEMAPHORE:
        with settings_lock:
            settings = load_settings()

        output_dir = resolve_output_dir(None)
        fragments = int(settings.get("concurrent_fragments") or 4)

        task_id = create_task(
            kind=kind,
            height=height,
            subtitle_lang=subtitle_lang,
            output_dir=str(output_dir),
            source="telegram",
            telegram_owner_user_id=query.from_user.id,
            local_deleted=False,
        )

        status_message = await query.message.reply_text(
            "⏳ 下载任务已创建…"
        )

        worker = asyncio.create_task(
            asyncio.to_thread(
                download_worker,
                task_id,
                session["url"],
                kind,
                height,
                subtitle_lang,
                output_dir,
                fragments,
            )
        )

        last_text = None

        while not worker.done():
            task = get_task(task_id)

            if task:
                text = task_text(task)

                if text != last_text:
                    await edit_progress_safely(status_message, text)
                    last_text = text

            # Telegram 单个聊天不宜过于频繁编辑消息。
            await asyncio.sleep(1.5)

        # 让线程异常真正传播出来（正常 download_worker 会自己写 error 状态）。
        try:
            await worker
        except Exception:
            pass

        task = get_task(task_id)

        if not task:
            await edit_progress_safely(
                status_message,
                "❌ 任务状态丢失",
            )
            return

        final_text = task_text(task)
        await edit_progress_safely(status_message, final_text)

        if task.get("status") == "done":
            await send_finished_file(query, task_id, task)


async def handle_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query
    user = update.effective_user

    if not query or not user:
        return

    await query.answer()

    if not is_authorized(user.id):
        await query.message.reply_text("未授权。")
        return

    data = query.data or ""

    if await handle_local_file_action(query, user.id, data):
        return

    parts = data.split(":")

    if len(parts) < 2:
        return

    action = parts[0]
    session_id = parts[1]
    session = get_session(session_id)

    if not session:
        await query.message.reply_text(
            "这个解析结果已经过期，请重新发送 Bilibili 链接。"
        )
        return

    try:
        if action == "v" and len(parts) == 3:
            height = int(parts[2])

            await run_download_from_callback(
                query,
                session,
                kind="video",
                height=height,
            )

        elif action == "a":
            await run_download_from_callback(
                query,
                session,
                kind="audio",
            )

        elif action == "c":
            await run_download_from_callback(
                query,
                session,
                kind="cover",
            )

        elif action == "s" and len(parts) == 3:
            index = int(parts[2])
            subtitles = session.get("subtitles") or []

            if index < 0 or index >= len(subtitles):
                raise ValueError("字幕轨不存在")

            lang = subtitles[index]["id"]

            await run_download_from_callback(
                query,
                session,
                kind="subtitle",
                subtitle_lang=lang,
            )

        elif action == "d":
            if not session.get("danmaku"):
                raise ValueError("这个视频没有可用弹幕")

            await run_download_from_callback(
                query,
                session,
                kind="danmaku",
            )

    except Exception as exc:
        await query.message.reply_text(
            f"❌ 操作失败\n\n{exc}"
        )


async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    # 不在聊天里泄露完整 traceback，只输出控制台日志。
    print(f"[Telegram Bot] Error: {context.error!r}")


def main() -> None:
    if not TOKEN:
        raise SystemExit(
            "没有检测到 TELEGRAM_BOT_TOKEN。\n"
            "请先运行 telegram_setup.bat。"
        )

    print("========================================")
    print(" MoonTrace Telegram Bot")
    print("========================================")

    if ALLOWED_USERS:
        print(
            "Allowed Telegram users:",
            ", ".join(str(x) for x in sorted(ALLOWED_USERS)),
        )
    else:
        print(
            "WARNING: TELEGRAM_ALLOWED_USERS 为空。"
            "Bot 只允许 /whoami 等基础命令，不允许下载。"
        )

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", command_start))
    app.add_handler(CommandHandler("help", command_help))
    app.add_handler(CommandHandler("whoami", command_whoami))
    app.add_handler(CommandHandler("status", command_status))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_link,
        )
    )

    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_error_handler(error_handler)

    print("Bot is running with long polling.")
    print("Press Ctrl+C to stop.")

    app.run_polling()


if __name__ == "__main__":
    main()

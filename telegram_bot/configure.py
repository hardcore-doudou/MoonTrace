from getpass import getpass
from pathlib import Path

from config import DATA_DIR


ENV_FILE = DATA_DIR / ".env"


def read_existing() -> dict[str, str]:
    result = {}

    if not ENV_FILE.exists():
        return result

    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()

    return result


def main() -> None:
    existing = read_existing()

    print()
    print("========================================")
    print(" MoonTrace Telegram 配置")
    print("========================================")
    print()
    print("Bot Token 从 Telegram 的 @BotFather 获取。")
    print("Token 不会上传 GitHub；.env 已加入 .gitignore。")
    print()

    old_token = existing.get("TELEGRAM_BOT_TOKEN", "")
    prompt = "Bot Token"

    if old_token:
        prompt += "（直接回车保留现有 Token）"

    prompt += "："

    token = getpass(prompt).strip()

    if not token:
        token = old_token

    if not token:
        print("没有填写 Bot Token，已取消。")
        return

    old_users = existing.get("TELEGRAM_ALLOWED_USERS", "")

    print()
    print("允许使用下载功能的 Telegram 数字用户 ID。")
    print("不知道 ID 可以先留空，启动 Bot 后发送 /whoami 查看，")
    print("再重新运行本配置脚本填写。")
    print("多个 ID 用英文逗号分隔。")
    print()

    users = input(
        f"允许用户 ID [{old_users or '未设置'}]："
    ).strip()

    if not users:
        users = old_users

    old_limit = existing.get("TELEGRAM_MAX_UPLOAD_MB", "49")
    limit = input(
        f"标准 Bot API 上传安全阈值 MB [{old_limit}]："
    ).strip()

    if not limit:
        limit = old_limit

    ENV_FILE.write_text(
        "# MoonTrace Telegram configuration\n"
        f"TELEGRAM_BOT_TOKEN={token}\n"
        f"TELEGRAM_ALLOWED_USERS={users}\n"
        f"TELEGRAM_MAX_UPLOAD_MB={limit}\n",
        encoding="utf-8",
    )

    print()
    print("已保存：", ENV_FILE)
    print()

    if users:
        print("Telegram Bot 已完成基本配置。")
    else:
        print(
            "尚未设置允许用户 ID。"
            "下一步启动 Bot 后发送 /whoami 获取 ID。"
        )


if __name__ == "__main__":
    main()

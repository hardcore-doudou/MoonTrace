"""SQLite task store shared by the Web server and Telegram process."""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock

from config import DATA_DIR


TASK_DB_PATH = DATA_DIR / "user_data" / "tasks.sqlite3"
ACTIVE = ("starting", "downloading", "processing")
TERMINAL = ("done", "error", "cancelled")
MAX_RUNNING = 2
_init_lock = Lock()
_initialized_path: Path | None = None

_COLUMNS = {
    "status", "title", "platform", "url", "kind", "height", "quality_id",
    "quality_label", "subtitle_lang", "output_dir", "concurrent_fragments",
    "filename", "filepath", "file_size", "progress", "speed", "eta",
    "components", "error", "source", "telegram_owner_user_id",
    "local_deleted", "retry_of", "worker_id",
    "group_id", "parent_id", "part_index", "selection",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@contextmanager
def _connection():
    global _initialized_path
    path = TASK_DB_PATH
    with _init_lock:
        if _initialized_path != path:
            path.parent.mkdir(parents=True, exist_ok=True)
            db = sqlite3.connect(path, timeout=15)
            try:
                db.execute("PRAGMA journal_mode=WAL")
                db.execute("PRAGMA busy_timeout=15000")
                db.execute("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        id TEXT PRIMARY KEY,
                        status TEXT NOT NULL,
                        title TEXT, platform TEXT, url TEXT, kind TEXT,
                        height INTEGER, quality_id INTEGER, quality_label TEXT,
                        subtitle_lang TEXT, output_dir TEXT,
                        concurrent_fragments INTEGER NOT NULL DEFAULT 4,
                        filename TEXT, filepath TEXT, file_size INTEGER,
                        progress REAL, speed REAL, eta REAL,
                        components TEXT NOT NULL DEFAULT '{}', error TEXT,
                        source TEXT, telegram_owner_user_id INTEGER,
                        local_deleted INTEGER NOT NULL DEFAULT 0,
                        retry_of TEXT, worker_id TEXT,
                        group_id TEXT, parent_id TEXT, part_index INTEGER,
                        selection TEXT NOT NULL DEFAULT '{}',
                        created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                        completed_at TEXT
                    )
                """)
                db.execute("CREATE INDEX IF NOT EXISTS tasks_status_created ON tasks(status, created_at)")
                db.execute("CREATE INDEX IF NOT EXISTS tasks_created ON tasks(created_at DESC)")
                db.commit()
            finally:
                db.close()
            _initialized_path = path
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=15000")
    try:
        with db:
            yield db
    finally:
        db.close()


def _as_task(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    task = dict(row)
    task["components"] = json.loads(task["components"] or "{}")
    task["selection"] = json.loads(task["selection"] or "{}")
    task["local_deleted"] = bool(task["local_deleted"])
    return task


def create_task(**data) -> str:
    unknown = data.keys() - _COLUMNS
    if unknown:
        raise ValueError(f"未知任务字段：{', '.join(sorted(unknown))}")
    task_id = uuid.uuid4().hex
    now = _now()
    values = {
        "id": task_id, "status": "queued", "progress": 0,
        "components": "{}", "created_at": now, "updated_at": now,
        **data,
    }
    if isinstance(values["components"], dict):
        values["components"] = json.dumps(values["components"], ensure_ascii=False)
    if isinstance(values.get("selection"), dict):
        values["selection"] = json.dumps(values["selection"], ensure_ascii=False)
    columns = ", ".join(values)
    placeholders = ", ".join("?" for _ in values)
    with _connection() as db:
        db.execute(
            f"INSERT INTO tasks ({columns}) VALUES ({placeholders})",
            tuple(values.values()),
        )
    return task_id


def get_task(task_id: str) -> dict | None:
    with _connection() as db:
        return _as_task(db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone())


def update_task(task_id: str, **changes) -> None:
    unknown = changes.keys() - _COLUMNS
    if unknown:
        raise ValueError(f"未知任务字段：{', '.join(sorted(unknown))}")
    if not changes:
        return
    if isinstance(changes.get("components"), dict):
        changes["components"] = json.dumps(changes["components"], ensure_ascii=False)
    if changes.get("status") == "done":
        changes.update(completed_at=_now(), speed=None, eta=None, progress=100)
    elif changes.get("status") in ("error", "cancelled"):
        changes.update(completed_at=_now(), speed=None, eta=None)
    changes["updated_at"] = _now()
    updates = ", ".join(f"{key} = ?" for key in changes)
    with _connection() as db:
        # A stale worker must not resurrect a task recovered after a crash.
        db.execute(
            f"UPDATE tasks SET {updates} WHERE id = ? AND "
            "(status NOT IN ('done', 'error', 'cancelled') OR "
            "(status = 'done' AND ? = 1))",
            (*changes.values(), task_id, int("local_deleted" in changes)),
        )


def update_progress(task_id: str, stream: str, status: str, **values) -> None:
    """Merge yt-dlp stream updates atomically, including concurrent fragments."""
    with _connection() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT status, kind, components FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None or row["status"] in TERMINAL:
            return
        components = json.loads(row["components"] or "{}")
        component = components.setdefault(stream, {})
        component.update(status=status, **values)
        if status == "done":
            component.update(progress=100, speed=None, eta=None)
        known = [part for part in components.values() if part.get("progress") is not None]
        if row["kind"] == "video" and stream != "file":
            # Video and audio are independent streams; one completed stream is ~half.
            progress = round(sum(components.get(key, {}).get("progress") or 0
                                 for key in ("video", "audio")) / 2, 1)
        else:
            progress = round(sum(part["progress"] for part in known) / len(known), 1) if known else 0
        speed = sum(part.get("speed") or 0 for part in components.values()) or None
        remaining = [part["eta"] for part in components.values() if part.get("eta") is not None]
        eta = max(remaining) if remaining else None
        stream_complete = (
            row["kind"] != "video" or stream == "file" or
            all(components.get(key, {}).get("status") == "done" for key in ("video", "audio"))
        )
        db.execute(
            """UPDATE tasks SET components = ?, status = ?, progress = ?,
               speed = ?, eta = ?, updated_at = ? WHERE id = ?""",
            (json.dumps(components, ensure_ascii=False),
             "processing" if status == "done" and stream_complete else "downloading",
             progress, speed, eta, _now(), task_id),
        )


def list_tasks(status: str, limit: int = 50, offset: int = 0) -> dict:
    groups = {
        "current": ACTIVE, "queued": ("queued",),
        "done": ("done",), "failed": ("error", "cancelled"),
    }
    if status not in groups:
        raise ValueError("未知任务分组")
    states = groups[status]
    placeholders = ",".join("?" for _ in states)
    order = "created_at ASC" if status in ("current", "queued") else "created_at DESC"
    with _connection() as db:
        total = db.execute(
            f"SELECT count(*) FROM tasks WHERE status IN ({placeholders})", states
        ).fetchone()[0]
        rows = db.execute(
            f"SELECT * FROM tasks WHERE status IN ({placeholders}) "
            f"ORDER BY {order}, id LIMIT ? OFFSET ?",
            (*states, limit, offset),
        ).fetchall()
    return {"items": [_as_task(row) for row in rows], "total": total}


def task_counts() -> dict:
    with _connection() as db:
        rows = db.execute("SELECT status, count(*) AS n FROM tasks GROUP BY status").fetchall()
    counts = {row["status"]: row["n"] for row in rows}
    return {
        "current": sum(counts.get(key, 0) for key in ACTIVE),
        "queued": counts.get("queued", 0),
        "done": counts.get("done", 0),
        "failed": counts.get("error", 0) + counts.get("cancelled", 0),
    }


def clear_history() -> int:
    with _connection() as db:
        cursor = db.execute("DELETE FROM tasks WHERE status IN ('done', 'error', 'cancelled')")
        return cursor.rowcount


def cancel_queued(task_id: str) -> bool:
    now = _now()
    with _connection() as db:
        result = db.execute(
            "UPDATE tasks SET status = 'cancelled', completed_at = ?, updated_at = ? "
            "WHERE id = ? AND status = 'queued'", (now, now, task_id)
        )
        return result.rowcount == 1


def claim_next(worker_id: str) -> dict | None:
    """Claim the oldest queued task across all MoonTrace processes."""
    now = _now()
    stale = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat(timespec="milliseconds")
    with _connection() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute(
            """UPDATE tasks SET status = 'error', error = '下载进程中断，请重新下载',
               completed_at = ?, updated_at = ?, speed = NULL, eta = NULL
               WHERE status IN ('starting', 'downloading', 'processing') AND updated_at < ?""",
            (now, now, stale),
        )
        count = db.execute(
            "SELECT count(*) FROM tasks WHERE status IN ('starting', 'downloading', 'processing')"
        ).fetchone()[0]
        if count >= MAX_RUNNING:
            return None
        row = db.execute(
            "SELECT * FROM tasks WHERE status = 'queued' ORDER BY created_at ASC, id LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        db.execute(
            "UPDATE tasks SET status = 'starting', worker_id = ?, updated_at = ? WHERE id = ?",
            (worker_id, now, row["id"]),
        )
        task = _as_task(row)
        task.update(status="starting", worker_id=worker_id)
        return task


def heartbeat(task_id: str, worker_id: str) -> None:
    with _connection() as db:
        db.execute(
            "UPDATE tasks SET updated_at = ? WHERE id = ? AND worker_id = ? "
            "AND status IN ('starting', 'downloading', 'processing')",
            (_now(), task_id, worker_id),
        )

"""Small process-local runner backed by the cross-process SQLite queue."""

from __future__ import annotations

import logging
import threading
import uuid
from pathlib import Path

from core.downloader import download_worker
from core.tasks import claim_next, create_task, get_task, heartbeat, update_task


_wake = threading.Event()
_start_lock = threading.Lock()
_runner: threading.Thread | None = None


def enqueue_download(**data) -> str:
    task_id = create_task(**data)
    start_queue()
    _wake.set()
    return task_id


def start_queue() -> None:
    global _runner
    with _start_lock:
        if _runner is None or not _runner.is_alive():
            _runner = threading.Thread(target=_run, daemon=True, name="moontrace-queue")
            _runner.start()


def _run() -> None:
    while True:
        try:
            worker_id = uuid.uuid4().hex
            task = claim_next(worker_id)
            if task:
                _execute(task, worker_id)
                continue
        except Exception:
            logging.exception("MoonTrace queue failed; retrying")
        _wake.wait(timeout=1)
        _wake.clear()


def _execute(task: dict, worker_id: str) -> None:
    def work() -> None:
        try:
            download_worker(
                task["id"], task["url"], task["kind"], task["height"],
                task["quality_id"], task["subtitle_lang"], Path(task["output_dir"]),
                task["concurrent_fragments"],
            )
        except Exception as exc:
            logging.exception("MoonTrace worker failed")
            update_task(task["id"], status="error", error=str(exc))

    thread = threading.Thread(target=work, daemon=True, name=f"download-{task['id'][:8]}")
    thread.start()
    while thread.is_alive():
        thread.join(timeout=2)
        heartbeat(task["id"], worker_id)
    if get_task(task["id"])["status"] in ("starting", "downloading", "processing"):
        update_task(task["id"], status="error", error="下载未能完成，请重试")

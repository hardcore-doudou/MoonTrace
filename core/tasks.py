from threading import Lock
import uuid


tasks: dict[str, dict] = {}
tasks_lock = Lock()


def create_task(**data) -> str:
    task_id = uuid.uuid4().hex

    with tasks_lock:
        tasks[task_id] = {
            "id": task_id,
            "status": "queued",
            "progress": 0,
            "filename": None,
            "filepath": None,
            "file_size": None,
            "components": {},
            "error": None,
            **data,
        }

    return task_id


def update_task(task_id: str, **changes) -> None:
    with tasks_lock:
        if task_id in tasks:
            tasks[task_id].update(changes)


def get_task(task_id: str) -> dict | None:
    with tasks_lock:
        task = tasks.get(task_id)
        return dict(task) if task else None

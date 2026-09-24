"""Windows desktop entry point for the existing FastAPI/Web task manager."""

from __future__ import annotations

import socket
import sys
import threading
import time


def main() -> None:
    if sys.platform != "win32":
        raise SystemExit("桌面窗口需要在 Windows 上运行；Web 版可用 start.bat 启动。")

    import uvicorn
    import webview

    from app import app
    from config import DATA_DIR

    # Bind before launching the server, so concurrent launches cannot pick the
    # same port. The HTTP API is reachable only from this computer.
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(128)
    port = listener.getsockname()[1]
    config = uvicorn.Config(
        app, host="127.0.0.1", port=port, log_level="warning", access_log=False,
    )
    server = uvicorn.Server(config)
    worker = threading.Thread(
        target=server.run, kwargs={"sockets": [listener]}, daemon=True,
        name="moontrace-web",
    )
    worker.start()

    try:
        for _ in range(100):
            if server.started:
                break
            if not worker.is_alive():
                raise RuntimeError("本地任务服务启动失败")
            time.sleep(0.1)
        else:
            raise RuntimeError("本地任务服务启动超时")

        window = webview.create_window(
            "MoonTrace", f"http://127.0.0.1:{port}/",
            width=1260, height=800, min_size=(900, 620),
        )
        # The browser profile stays outside the executable and survives updates.
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        webview.start(gui="edgechromium", storage_path=str(DATA_DIR / "webview"))
    finally:
        server.should_exit = True
        worker.join(timeout=5)
        listener.close()


if __name__ == "__main__":
    main()

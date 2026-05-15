from __future__ import annotations

import os
import shutil
import socket
import subprocess
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any

from .api import create_app
from .config import Settings


def _browser_host(host: str) -> str:
    return "127.0.0.1" if host in {"0.0.0.0", "::"} else host


def _is_port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((_browser_host(host), port), timeout=0.25):
            return True
    except OSError:
        return False


def _pick_port(host: str, preferred: int) -> int:
    port = preferred
    while _is_port_open(host, port):
        port += 1
    return port


def _wait_for_port(host: str, port: int, timeout_seconds: float = 30.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if _is_port_open(host, port):
            return
        time.sleep(0.2)
    raise RuntimeError(f"端口未在预期时间内可用：{host}:{port}")


def _path_value(path: Path | None) -> str | None:
    return str(path.resolve()) if path else None


def _npm_command() -> str:
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if not npm:
        raise RuntimeError("未找到 npm。请先安装 Node.js 20+，或确认 npm 已加入 PATH。")
    return npm


def _ensure_frontend_dependencies(vue_dir: Path) -> None:
    if not (vue_dir / "package.json").is_file():
        raise RuntimeError(f"未找到前端工程：{vue_dir}")
    if (vue_dir / "node_modules").is_dir():
        return
    print("首次启动 web 端，正在安装前端依赖（npm install）...")
    subprocess.run([_npm_command(), "install"], cwd=vue_dir, check=True)


def _start_api_server(settings: Settings, host: str, port: int, startup_config: dict[str, Any]):
    import uvicorn

    app = create_app(settings, startup_config=startup_config)
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="overall-situation-api", daemon=True)
    thread.start()
    _wait_for_port(host, port)
    return server, thread


def launch_web(
    *,
    settings: Settings,
    project_dir: Path,
    host: str,
    api_port: int,
    web_port: int,
    import_input: Path | None = None,
    schedule_input: Path | None = None,
    recreate_index: bool = False,
    start_date: str | None = None,
    end_date: str | None = None,
    output: Path | None = None,
) -> None:
    project_dir = project_dir.resolve()
    vue_dir = project_dir / "vue_app"
    api_port = _pick_port(host, api_port)
    web_port = _pick_port(host, web_port)
    browser_host = _browser_host(host)
    api_url = f"http://{browser_host}:{api_port}"
    web_url = f"http://{browser_host}:{web_port}"

    startup_config: dict[str, Any] = {
        "import_input": _path_value(import_input),
        "schedule_input": _path_value(schedule_input),
        "recreate_index": recreate_index,
        "start_date": start_date,
        "end_date": end_date,
        "output": _path_value(output),
        "api_url": api_url,
        "api_port": api_port,
        "web_url": web_url,
        "web_port": web_port,
    }

    _ensure_frontend_dependencies(vue_dir)
    api_server, api_thread = _start_api_server(settings, host, api_port, startup_config)

    env = os.environ.copy()
    env["VITE_API_TARGET"] = api_url
    npm = _npm_command()
    vite_command = [
        npm,
        "run",
        "dev",
        "--",
        "--host",
        host,
        "--port",
        str(web_port),
        "--strictPort",
    ]
    vite_process = subprocess.Popen(vite_command, cwd=vue_dir, env=env)

    try:
        _wait_for_port(host, web_port)
        print(f"API 服务：{api_url}")
        print(f"Web 端：{web_url}")
        print("正在使用默认浏览器打开 web 端...")
        webbrowser.open(web_url)
        while vite_process.poll() is None:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("正在关闭 web 端与 API 服务...")
    finally:
        if vite_process.poll() is None:
            vite_process.terminate()
            try:
                vite_process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                vite_process.kill()
        api_server.should_exit = True
        api_thread.join(timeout=8)

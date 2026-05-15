from __future__ import annotations

import asyncio
import mimetypes
import queue
import re
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from .agent import OverallSituationAgent
from .config import Settings, load_settings
from .interactive_app import InteractiveOverallSituationApp


class ImportRequest(BaseModel):
    input: Path
    recreate_index: bool = False


class ReportRequest(BaseModel):
    output: Path | None = None
    start_date: str | None = None
    end_date: str | None = None
    schedule_input: Path | None = None


class RunRequest(ReportRequest):
    input: Path
    recreate_index: bool = False


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    schedule_input: Path | None = None


UPLOAD_SUFFIXES = {".xlsx", ".xlsm"}
REPORT_SUFFIXES = {".html", ".md"}


@dataclass
class JobRecord:
    id: str
    kind: str
    status: str = "queued"
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    events: "queue.Queue[dict[str, Any]]" = field(default_factory=queue.Queue)

    def public(self) -> dict[str, Any]:
        return {
            "job_id": self.id,
            "kind": self.kind,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=2)

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._jobs.get(job_id)

    def submit(self, kind: str, work: Callable[[Callable[[str, dict[str, Any] | None], None]], dict[str, Any]]) -> JobRecord:
        job = JobRecord(id=uuid.uuid4().hex, kind=kind)
        with self._lock:
            self._jobs[job.id] = job

        def emit(event: str, data: dict[str, Any] | None = None) -> None:
            payload = {"event": event, "data": data or {}, "time": datetime.now().isoformat(timespec="seconds")}
            job.events.put(payload)

        def runner() -> None:
            try:
                job.status = "running"
                job.updated_at = datetime.now().isoformat(timespec="seconds")
                emit("started", {"job_id": job.id, "kind": job.kind})
                result = work(emit)
                job.result = result
                job.status = "completed"
                job.updated_at = datetime.now().isoformat(timespec="seconds")
                emit("completed", result)
            except Exception as exc:  # pragma: no cover - exercised through API integration tests if added.
                job.error = str(exc)
                job.status = "failed"
                job.updated_at = datetime.now().isoformat(timespec="seconds")
                emit("failed", {"error": job.error})

        self._executor.submit(runner)
        return job


class ChatSessionStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._sessions: dict[str, InteractiveOverallSituationApp] = {}
        self._lock = threading.Lock()

    def get(self, session_id: str | None, schedule_input: Path | None = None) -> tuple[str, InteractiveOverallSituationApp]:
        sid = session_id or uuid.uuid4().hex
        with self._lock:
            session = self._sessions.get(sid)
            if session is None:
                session = InteractiveOverallSituationApp(self.settings, schedule_input=schedule_input)
                self._sessions[sid] = session
            return sid, session


def _report_url(path: Path, outputs_dir: Path) -> str | None:
    resolved = path.resolve()
    output_root = outputs_dir.resolve()
    if resolved.parent != output_root or resolved.suffix.lower() not in REPORT_SUFFIXES:
        return None
    return f"/api/reports/{quote(resolved.name)}"


def _path_result(path: Path, outputs_dir: Path) -> dict[str, str | None]:
    html_path = path.resolve()
    markdown_path = html_path.with_suffix(".md")
    return {
        "html_path": str(html_path),
        "markdown_path": str(markdown_path),
        "html_url": _report_url(html_path, outputs_dir),
        "markdown_url": _report_url(markdown_path, outputs_dir),
    }


def _safe_upload_name(filename: str) -> str:
    raw_name = Path(filename or "upload.xlsx").name
    stem = Path(raw_name).stem or "upload"
    suffix = Path(raw_name).suffix.lower()
    cleaned_stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", stem).strip(" ._") or "upload"
    return f"{cleaned_stem[:80]}{suffix}"


def _resolve_report_file(outputs_dir: Path, filename: str) -> Path:
    requested_name = Path(filename).name
    candidate = (outputs_dir / requested_name).resolve()
    output_root = outputs_dir.resolve()
    if candidate.parent != output_root or candidate.suffix.lower() not in REPORT_SUFFIXES:
        raise HTTPException(status_code=404, detail="report not found")
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="report not found")
    return candidate


def create_app(settings: Settings | None = None, startup_config: dict[str, Any] | None = None) -> FastAPI:
    app_settings = settings or load_settings(Path.cwd())
    app = FastAPI(title="Overall Situation Agent API")
    jobs = JobStore()
    sessions = ChatSessionStore(app_settings)
    upload_root = (app_settings.logs_dir.parent / ".uploads").resolve()
    web_startup = dict(startup_config or {})

    def make_agent() -> OverallSituationAgent:
        return OverallSituationAgent(app_settings)

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "es_index": app_settings.es_index}

    @app.get("/api/web/startup")
    def web_startup_config() -> dict[str, Any]:
        return {
            "status": "ok",
            "project_dir": str(app_settings.logs_dir.parent.resolve()),
            "es_index": app_settings.es_index,
            "outputs_dir": str(app_settings.outputs_dir.resolve()),
            "uploads_dir": str(upload_root),
            "llm_enabled": bool(app_settings.llm_api_key),
            "llm_report_enabled": app_settings.llm_report_enabled,
            "defaults": web_startup,
        }

    @app.post("/api/uploads")
    async def upload_files(files: list[UploadFile] = File(...)) -> dict[str, Any]:
        if not files:
            raise HTTPException(status_code=400, detail="no files uploaded")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        target_dir = upload_root / timestamp
        target_dir.mkdir(parents=True, exist_ok=True)

        saved_paths: list[Path] = []
        for upload in files:
            filename = _safe_upload_name(upload.filename or "upload.xlsx")
            suffix = Path(filename).suffix.lower()
            if suffix not in UPLOAD_SUFFIXES:
                raise HTTPException(status_code=400, detail=f"unsupported file type: {filename}")

            target = target_dir / filename
            with target.open("wb") as handle:
                while True:
                    chunk = await upload.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
            await upload.close()
            saved_paths.append(target.resolve())

        input_path = saved_paths[0] if len(saved_paths) == 1 else target_dir.resolve()
        return {
            "count": len(saved_paths),
            "input_path": str(input_path),
            "files": [str(path) for path in saved_paths],
        }

    @app.get("/api/reports/{filename}")
    def report_file(filename: str) -> FileResponse:
        path = _resolve_report_file(app_settings.outputs_dir, filename)
        media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        return FileResponse(path, media_type=media_type, filename=path.name)

    @app.post("/api/import")
    def import_data(request: ImportRequest) -> dict[str, Any]:
        result = make_agent().import_data(request.input, recreate_index=request.recreate_index)
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        return {"count": result.count, "imported": result.imported, "message": result.message}

    @app.post("/api/report")
    def report(request: ReportRequest) -> dict[str, Any]:
        path = make_agent().generate_report(
            output_path=request.output,
            start_date=request.start_date,
            end_date=request.end_date,
            schedule_input=request.schedule_input,
        )
        return _path_result(path, app_settings.outputs_dir)

    @app.post("/api/run")
    def run(request: RunRequest) -> dict[str, Any]:
        path = make_agent().run(
            input_path=request.input,
            output_path=request.output,
            start_date=request.start_date,
            end_date=request.end_date,
            recreate_index=request.recreate_index,
            schedule_input=request.schedule_input,
        )
        return _path_result(path, app_settings.outputs_dir)

    @app.post("/api/chat")
    def chat(request: ChatRequest) -> dict[str, Any]:
        session_id, session = sessions.get(request.session_id, schedule_input=request.schedule_input)
        answer = session.handle_message(request.message)
        payload: dict[str, Any] = {"session_id": session_id, "answer": answer}
        if session.state.last_report_path:
            payload["report_paths"] = _path_result(session.state.last_report_path, app_settings.outputs_dir)
        return payload

    def submit_import(request: ImportRequest) -> JobRecord:
        return jobs.submit(
            "import",
            lambda emit: (
                emit("stage", {"message": "importing"}),
                import_data(request),
            )[1],
        )

    def submit_report(request: ReportRequest) -> JobRecord:
        return jobs.submit(
            "report",
            lambda emit: (
                emit("stage", {"message": "generating_report"}),
                report(request),
            )[1],
        )

    def submit_run(request: RunRequest) -> JobRecord:
        return jobs.submit(
            "run",
            lambda emit: (
                emit("stage", {"message": "importing_and_generating_report"}),
                run(request),
            )[1],
        )

    def submit_chat(request: ChatRequest) -> JobRecord:
        return jobs.submit(
            "chat",
            lambda emit: (
                emit("stage", {"message": "handling_chat_message"}),
                chat(request),
            )[1],
        )

    @app.post("/api/jobs/import")
    def job_import(request: ImportRequest) -> dict[str, Any]:
        return submit_import(request).public()

    @app.post("/api/jobs/report")
    def job_report(request: ReportRequest) -> dict[str, Any]:
        return submit_report(request).public()

    @app.post("/api/jobs/run")
    def job_run(request: RunRequest) -> dict[str, Any]:
        return submit_run(request).public()

    @app.post("/api/jobs/chat")
    def job_chat(request: ChatRequest) -> dict[str, Any]:
        return submit_chat(request).public()

    @app.get("/api/jobs/{job_id}")
    def job_status(job_id: str) -> dict[str, Any]:
        job = jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        return job.public()

    @app.get("/api/jobs/{job_id}/events")
    async def job_events(job_id: str) -> EventSourceResponse:
        job = jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")

        async def event_generator():
            while True:
                try:
                    item = job.events.get_nowait()
                    yield {"event": item["event"], "data": item["data"]}
                    if item["event"] in {"completed", "failed"}:
                        break
                except queue.Empty:
                    if job.status in {"completed", "failed"}:
                        yield {"event": job.status, "data": job.result or {"error": job.error}}
                        break
                    await asyncio.sleep(0.5)

        return EventSourceResponse(event_generator())

    return app


app = create_app()

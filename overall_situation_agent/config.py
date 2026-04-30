from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    load_dotenv = None


def _load_env_file(path: Path) -> None:
    if load_dotenv is not None:
        load_dotenv(path)
        return
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Settings:
    es_url: str = "http://localhost:9200"
    es_index: str = "tagged_feedback"
    es_username: str | None = None
    es_password: str | None = None
    es_verify_certs: bool = False
    llm_base_url: str = "https://api.deepseek.com"
    llm_api_key: str | None = None
    llm_model: str = "deepseek-chat"
    llm_timeout_seconds: int = 45
    llm_max_retries: int = 2
    llm_report_timeout_seconds: int = 12
    llm_report_max_retries: int = 0
    llm_report_max_tokens: int = 2500
    llm_report_enabled: bool = False
    import_batch_size: int = 500
    outputs_dir: Path = Path("outputs")
    logs_dir: Path = Path("logs")
    import_state_file: Path = Path("logs/import_state.json")


def load_settings(project_dir: Path | None = None) -> Settings:
    if project_dir:
        _load_env_file(project_dir / ".env")
    else:
        _load_env_file(Path.cwd() / ".env")

    username = os.getenv("ES_USERNAME") or None
    password = os.getenv("ES_PASSWORD") or None
    verify_certs = (os.getenv("ES_VERIFY_CERTS", "false").lower() == "true")
    project_root = project_dir or Path.cwd()

    outputs_dir = Path(os.getenv("OUTPUTS_DIR", project_root / "outputs"))
    logs_dir = Path(os.getenv("LOGS_DIR", project_root / "logs"))
    if not outputs_dir.is_absolute():
        outputs_dir = project_root / outputs_dir
    if not logs_dir.is_absolute():
        logs_dir = project_root / logs_dir
    import_state_file = Path(os.getenv("IMPORT_STATE_FILE", logs_dir / "import_state.json"))
    if not import_state_file.is_absolute():
        import_state_file = project_root / import_state_file

    return Settings(
        es_url=os.getenv("ES_URL", "http://localhost:9200"),
        es_index=os.getenv("ES_INDEX", "tagged_feedback"),
        es_username=username,
        es_password=password,
        es_verify_certs=verify_certs,
        llm_base_url=os.getenv("LLM_BASE_URL", "https://api.deepseek.com").rstrip("/"),
        llm_api_key=os.getenv("LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or None,
        llm_model=os.getenv("LLM_MODEL", "deepseek-chat"),
        llm_timeout_seconds=int(os.getenv("LLM_TIMEOUT_SECONDS", "45")),
        llm_max_retries=int(os.getenv("LLM_MAX_RETRIES", "2")),
        llm_report_timeout_seconds=int(os.getenv("LLM_REPORT_TIMEOUT_SECONDS", "12")),
        llm_report_max_retries=int(os.getenv("LLM_REPORT_MAX_RETRIES", "0")),
        llm_report_max_tokens=int(os.getenv("LLM_REPORT_MAX_TOKENS", "2500")),
        llm_report_enabled=os.getenv("LLM_REPORT_ENABLED", "false").lower() == "true",
        import_batch_size=int(os.getenv("IMPORT_BATCH_SIZE", "500")),
        outputs_dir=outputs_dir,
        logs_dir=logs_dir,
        import_state_file=import_state_file,
    )

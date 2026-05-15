from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from overall_situation_agent.api import _path_result, create_app
from overall_situation_agent.config import Settings


def _settings_for(base: Path) -> Settings:
    logs_dir = base / "logs"
    outputs_dir = base / "outputs"
    logs_dir.mkdir()
    outputs_dir.mkdir()
    return Settings(
        outputs_dir=outputs_dir,
        logs_dir=logs_dir,
        import_state_file=logs_dir / "import_state.json",
    )


class WebApiTests(unittest.TestCase):
    def test_upload_excel_files_to_uploads_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = _settings_for(Path(tmp))
            app = create_app(settings)
            client = TestClient(app)

            response = client.post(
                "/api/uploads",
                files=[("files", ("data.xlsx", b"fake workbook bytes", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))],
            )

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["count"], 1)
            saved_path = Path(payload["input_path"])
            self.assertTrue(saved_path.is_file())
            self.assertEqual(saved_path.suffix, ".xlsx")
            self.assertEqual(saved_path.read_bytes(), b"fake workbook bytes")
            self.assertEqual(saved_path.parents[1], Path(tmp) / ".uploads")

    def test_upload_rejects_non_excel_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = _settings_for(Path(tmp))
            app = create_app(settings)
            client = TestClient(app)

            response = client.post(
                "/api/uploads",
                files=[("files", ("data.txt", b"not excel", "text/plain"))],
            )

            self.assertEqual(response.status_code, 400)

    def test_report_files_are_served_only_from_outputs_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            settings = _settings_for(base)
            report_path = settings.outputs_dir / "report.html"
            report_path.write_text("<h1>ok</h1>", encoding="utf-8")
            (settings.outputs_dir / "report.md").write_text("# ok", encoding="utf-8")
            (base / "secret.md").write_text("secret", encoding="utf-8")

            app = create_app(settings)
            client = TestClient(app)

            response = client.get("/api/reports/report.html")
            self.assertEqual(response.status_code, 200)
            self.assertIn("<h1>ok</h1>", response.text)

            missing = client.get("/api/reports/secret.md")
            self.assertEqual(missing.status_code, 404)

            payload = _path_result(report_path, settings.outputs_dir)
            self.assertEqual(payload["html_url"], "/api/reports/report.html")
            self.assertEqual(payload["markdown_url"], "/api/reports/report.md")

    def test_web_startup_returns_non_secret_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = _settings_for(Path(tmp))
            app = create_app(settings, startup_config={"import_input": "C:/data/input.xlsx", "recreate_index": True})
            client = TestClient(app)

            response = client.get("/api/web/startup")

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["es_index"], "tagged_feedback")
            self.assertEqual(payload["defaults"]["import_input"], "C:/data/input.xlsx")
            self.assertTrue(payload["defaults"]["recreate_index"])
            self.assertNotIn("llm_api_key", payload)


if __name__ == "__main__":
    unittest.main()

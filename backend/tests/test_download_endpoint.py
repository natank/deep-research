import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)


def test_download_report_returns_file_contents(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "reports_dir", str(tmp_path))
    report_id = str(uuid.uuid4())
    (tmp_path / f"{report_id}.md").write_text("# Report", encoding="utf-8")

    response = client.get(f"/reports/{report_id}")

    assert response.status_code == 200
    assert response.text == "# Report"


def test_download_report_404s_for_missing_report(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "reports_dir", str(tmp_path))

    response = client.get(f"/reports/{uuid.uuid4()}")

    assert response.status_code == 404


def test_download_report_404s_for_invalid_id() -> None:
    response = client.get("/reports/../../etc/passwd")

    assert response.status_code == 404

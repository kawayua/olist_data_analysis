import json

from src.validation.quality import write_quality_report


def test_write_quality_report_creates_readable_json(tmp_path):
    path = tmp_path / "latest.json"
    report = {"tables": {"orders": {"row_count": 1}}}

    write_quality_report(report, path)

    assert json.loads(path.read_text(encoding="utf-8")) == report

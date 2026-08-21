from __future__ import annotations

import json
from pathlib import Path

from scripts.run_quality_checks import main, run_quality_checks


def test_run_quality_checks_writes_report_to_requested_path(tmp_path: Path) -> None:
    output_path = tmp_path / "nested" / "quality.json"
    report = {"tables": {"orders": {"row_count": 1}}}

    written_path = run_quality_checks(
        output_path,
        engine=object(),
        report_builder=lambda _: report,
    )

    assert written_path == output_path
    assert json.loads(output_path.read_text(encoding="utf-8")) == report


def test_main_uses_injected_settings_engine_and_quality_functions(
    tmp_path: Path, capsys
) -> None:
    output_path = tmp_path / "latest.json"
    settings = object()
    engine = object()
    calls: list[object] = []

    exit_code = main(
        output_path=output_path,
        settings_factory=lambda: settings,
        engine_factory=lambda actual_settings: (
            calls.append(actual_settings) or engine
        ),
        report_builder=lambda actual_engine: (
            calls.append(actual_engine) or {"business_checks": {}}
        ),
        report_writer=lambda report, path: calls.append((report, path)),
    )

    assert exit_code == 0
    assert calls == [settings, engine, ({"business_checks": {}}, output_path)]
    assert capsys.readouterr().out == f"Wrote quality report to {output_path}\n"

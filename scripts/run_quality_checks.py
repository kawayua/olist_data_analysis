"""Write the read-only database quality report required for local delivery."""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import get_settings
from src.database import get_engine
from src.validation.quality import build_quality_report, write_quality_report

OUTPUT_PATH = PROJECT_ROOT / "artifacts" / "quality" / "latest.json"
QualityReport = dict[str, object]


def run_quality_checks(
    output_path: Path = OUTPUT_PATH,
    *,
    engine: object | None = None,
    settings_factory: Callable[[], object] = get_settings,
    engine_factory: Callable[[object], object] = get_engine,
    report_builder: Callable[[object], QualityReport] = build_quality_report,
    report_writer: Callable[[QualityReport, Path], None] = write_quality_report,
) -> Path:
    """Build read-only checks and write their report to ``output_path``."""

    resolved_engine = (
        engine if engine is not None else engine_factory(settings_factory())
    )
    report_writer(report_builder(resolved_engine), output_path)
    return output_path


def main(
    *,
    output_path: Path = OUTPUT_PATH,
    settings_factory: Callable[[], object] = get_settings,
    engine_factory: Callable[[object], object] = get_engine,
    report_builder: Callable[[object], QualityReport] = build_quality_report,
    report_writer: Callable[[QualityReport, Path], None] = write_quality_report,
) -> int:
    """Run quality checks and return a conventional command exit status."""

    written_path = run_quality_checks(
        output_path,
        settings_factory=settings_factory,
        engine_factory=engine_factory,
        report_builder=report_builder,
        report_writer=report_writer,
    )
    print(f"Wrote quality report to {written_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

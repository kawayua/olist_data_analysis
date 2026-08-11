"""Load Olist source CSVs into PostgreSQL raw tables and create a quality report."""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import get_settings
from src.database import get_engine
from src.ingestion.contracts import CONTRACTS
from src.ingestion.loader import load_dataset
from src.validation.quality import build_quality_report, write_quality_report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    arguments = parser.parse_args()
    data_dir = arguments.data_dir.resolve()
    engine = get_engine(get_settings())

    results = []
    for contract in CONTRACTS.values():
        source_path = data_dir / contract.filename
        if not source_path.is_file():
            raise FileNotFoundError(f"Required dataset file is missing: {source_path}")
        result = load_dataset(engine, source_path, contract)
        results.append(result)
        print(f"{contract.name}: {result.status} ({result.row_count:,} rows)")

    failures = [result for result in results if result.status == "failed"]
    if failures:
        raise RuntimeError(f"{len(failures)} dataset(s) failed validation")

    report = build_quality_report(engine)
    report_path = PROJECT_ROOT / "artifacts" / "quality" / "latest.json"
    write_quality_report(report, report_path)
    print(f"Wrote quality report to {report_path.relative_to(PROJECT_ROOT).as_posix()}")


if __name__ == "__main__":
    main()

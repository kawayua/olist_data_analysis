"""Rebuild governed analysis marts from the warehouse layer."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    from src.config import get_settings
    from src.database import get_engine, run_sql, run_sql_file

    engine = get_engine(get_settings())
    run_sql(engine, "DROP TABLE IF EXISTS marts.cohort_retention")
    path = PROJECT_ROOT / "sql" / "marts" / "031_cohort_retention.sql"
    run_sql_file(engine, path)
    print(f"Applied {path.relative_to(PROJECT_ROOT).as_posix()}")


if __name__ == "__main__":
    main()

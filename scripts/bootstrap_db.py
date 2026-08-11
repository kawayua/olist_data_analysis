"""Create the PostgreSQL schemas required by the analytics platform."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import get_settings
from src.database import get_engine, run_sql_file


def main() -> None:
    bootstrap_dir = PROJECT_ROOT / "sql" / "bootstrap"
    engine = get_engine(get_settings())

    for path in sorted(bootstrap_dir.glob("*.sql")):
        run_sql_file(engine, path)
        relative_path = path.relative_to(PROJECT_ROOT).as_posix()
        print(f"Applied {relative_path}")


if __name__ == "__main__":
    main()

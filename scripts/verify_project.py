"""Non-destructive local readiness verification for the project."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

REQUIRED_SCHEMAS = ("raw", "staging", "warehouse", "marts")
REQUIRED_MARTS = (
    "monthly_growth",
    "cohort_retention",
    "repurchase_horizons",
    "customer_360",
    "customer_segment_strategy",
    "product_performance",
    "delivery_experience",
    "delivery_order_analysis",
    "state_performance",
    "customer_value_analysis",
    "repurchase_behavior",
    "repurchase_intervals",
    "delivery_rating_analysis",
    "state_monthly_performance",
    "ml_customer_features",
)
REQUIRED_RAW_TABLES = (
    "customers",
    "orders",
    "order_items",
    "reviews",
    "payments",
    "products",
)
REQUIRED_WAREHOUSE_TABLES = (
    "fact_orders",
    "fact_order_items",
    "fact_reviews",
    "dim_customer",
    "dim_product",
)
REQUIRED_ARTIFACTS = (
    "artifacts/quality/latest.json",
    "artifacts/models/repurchase_pipeline.joblib",
    "artifacts/models/metrics.json",
    "artifacts/agent/evaluation.json",
)
REQUIRED_RAW_FILES = (
    "olist_customers_dataset.csv",
    "olist_orders_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "olist_geolocation_dataset.csv",
    "product_category_name_translation.csv",
)
FULL_COMMANDS = (
    (
        "py",
        "-3.13",
        "-m",
        "pytest",
        "-v",
        "tests/test_config.py",
        "tests/agent/test_client.py",
        "tests/analytics/test_metrics.py",
        "tests/analytics/test_retention.py",
        "tests/analytics/test_segmentation.py",
        "tests/analytics/test_statistics.py",
        "tests/integration/test_end_to_end.py",
        "tests/integration/test_verify_project.py",
        "tests/ml/test_roi.py",
        "tests/validation/test_checks.py",
        "tests/visualization/test_charts.py",
        "tests/visualization/test_navigation.py",
    ),
    ("py", "-3.13", "-m", "ruff", "check", "src", "tests", "app", "scripts"),
)


@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    messages: tuple[str, ...]


@dataclass(frozen=True)
class VerificationDependencies:
    """External observations used by ``verify_project``.

    Each callable is read-only so test suites can replace infrastructure with
    deterministic fakes and the verifier never changes project state.
    """

    root: Path
    docker_available: Callable[[], bool]
    database_ready: Callable[[], bool]
    available_schemas: Callable[[], set[str]]
    available_raw_tables: Callable[[], set[str]]
    available_warehouse_tables: Callable[[], set[str]]
    available_marts: Callable[[], set[str]]
    is_env_tracked: Callable[[], bool]
    is_env_ignored: Callable[[], bool]
    run_command: Callable[[Sequence[str]], bool]


def _run_quietly(command: Sequence[str], *, cwd: Path, timeout: int = 15) -> bool:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return completed.returncode == 0


def _database_observation(query: str) -> set[str] | None:
    try:
        from sqlalchemy import text
        from sqlalchemy.exc import SQLAlchemyError

        from src.config import get_settings
        from src.database import get_engine

        with get_engine(get_settings()).connect() as connection:
            return {str(value) for value in connection.execute(text(query)).scalars()}
    except (OSError, RuntimeError, SQLAlchemyError):
        # Database errors must not disclose connection details.
        return None


def default_dependencies(root: Path = PROJECT_ROOT) -> VerificationDependencies:
    """Return read-only local observations for the command-line verifier."""

    def database_ready() -> bool:
        return _database_observation("SELECT 'ready'") == {"ready"}

    def available_schemas() -> set[str]:
        return _database_observation(
            "SELECT schema_name FROM information_schema.schemata"
        ) or set()

    def available_marts() -> set[str]:
        return _database_observation(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'marts'"
        ) or set()

    def available_raw_tables() -> set[str]:
        return _database_observation(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'raw'"
        ) or set()

    def available_warehouse_tables() -> set[str]:
        return _database_observation(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'warehouse'"
        ) or set()

    return VerificationDependencies(
        root=root,
        docker_available=lambda: _run_quietly(
            ("docker", "info"), cwd=root, timeout=15
        ),
        database_ready=database_ready,
        available_schemas=available_schemas,
        available_raw_tables=available_raw_tables,
        available_warehouse_tables=available_warehouse_tables,
        available_marts=available_marts,
        is_env_tracked=lambda: _run_quietly(
            ("git", "ls-files", "--error-unmatch", ".env"), cwd=root, timeout=15
        ),
        is_env_ignored=lambda: _run_quietly(
            ("git", "check-ignore", "--quiet", ".env"), cwd=root, timeout=15
        ),
        run_command=lambda command: _run_quietly(command, cwd=root, timeout=600),
    )


def _artifact_guidance(relative_path: str) -> str:
    if relative_path.startswith("artifacts/models/"):
        return "Run py -3.13 scripts/train_model.py to recreate model artifacts."
    if relative_path == "artifacts/agent/evaluation.json":
        return "Run py -3.13 scripts/evaluate_agent.py --mode fake to recreate it."
    return "Run py -3.13 scripts/run_quality_checks.py to recreate the quality artifact."


def _artifact_is_readable(artifact: Path) -> bool:
    """Validate generated artifacts without executing serialized model code."""

    try:
        if not artifact.is_file() or artifact.stat().st_size == 0:
            return False
        if artifact.suffix == ".json":
            with artifact.open(encoding="utf-8") as file:
                json.load(file)
        else:
            with artifact.open("rb") as file:
                return bool(file.read(1))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    return True


def verify_project(
    dependencies: VerificationDependencies,
    *,
    require_source_data: bool,
    full: bool,
) -> VerificationResult:
    """Observe local delivery readiness without importing data or starting services."""

    messages: list[str] = []
    if not dependencies.docker_available():
        messages.append("Docker is unavailable. Start Docker Desktop, then run docker compose up -d.")

    if not dependencies.database_ready():
        messages.append("Database check failed. Run docker compose up -d after Docker Desktop is ready.")
    else:
        available_schemas = dependencies.available_schemas()
        missing_schemas = sorted(set(REQUIRED_SCHEMAS) - available_schemas)
        if missing_schemas:
            messages.append(
                "Missing database schemas: "
                f"{', '.join(missing_schemas)}. "
                "Run py -3.13 scripts/bootstrap_db.py."
            )

        available_raw_tables = (
            dependencies.available_raw_tables() if "raw" in available_schemas else set()
        )
        missing_raw_tables = sorted(set(REQUIRED_RAW_TABLES) - available_raw_tables)
        if missing_raw_tables:
            messages.append(
                "Missing raw source tables: "
                f"{', '.join(missing_raw_tables)}. See data/README.md, then run "
                "py -3.13 scripts/load_raw.py --data-dir data/raw."
            )

        available_warehouse_tables = (
            dependencies.available_warehouse_tables()
            if "warehouse" in available_schemas
            else set()
        )
        missing_warehouse_tables = sorted(
            set(REQUIRED_WAREHOUSE_TABLES) - available_warehouse_tables
        )
        if missing_warehouse_tables:
            messages.append(
                "Missing warehouse tables: "
                f"{', '.join(missing_warehouse_tables)}. "
                "Run py -3.13 scripts/build_warehouse.py."
            )

        if not missing_raw_tables and not missing_warehouse_tables:
            available_marts = (
                dependencies.available_marts() if "marts" in available_schemas else set()
            )
            missing_marts = sorted(set(REQUIRED_MARTS) - available_marts)
            if missing_marts:
                messages.append(
                    "Missing marts: "
                    f"{', '.join(missing_marts)}. Run py -3.13 scripts/build_marts.py."
                )

    for relative_path in REQUIRED_ARTIFACTS:
        artifact = dependencies.root / relative_path
        if not _artifact_is_readable(artifact):
            messages.append(f"Missing or unreadable {relative_path}. {_artifact_guidance(relative_path)}")

    if dependencies.is_env_tracked():
        messages.append(".env is tracked by git; remove it from version control before delivery.")
    if not dependencies.is_env_ignored():
        messages.append(".env is not ignored by git; add it to .gitignore before delivery.")

    if require_source_data:
        missing_raw = [
            filename
            for filename in REQUIRED_RAW_FILES
            if not (dependencies.root / "data" / "raw" / filename).is_file()
        ]
        if missing_raw:
            messages.append(
                "Missing required source data: "
                f"{', '.join(missing_raw)}. See data/README.md, then run "
                "py -3.13 scripts/load_raw.py --data-dir data/raw."
            )

    if messages:
        return VerificationResult(ok=False, messages=tuple(messages))

    if full:
        for command in FULL_COMMANDS:
            if not dependencies.run_command(command):
                return VerificationResult(
                    ok=False,
                    messages=(f"Full verification failed: {' '.join(command)}",),
                )

    return VerificationResult(ok=True, messages=("Project readiness checks passed.",))


def main(
    argv: Sequence[str] | None = None,
    *,
    dependencies: VerificationDependencies | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true", help="also run tests and Ruff")
    parser.add_argument(
        "--require-source-data",
        action="store_true",
        help="require the nine CSV files documented in data/README.md",
    )
    args = parser.parse_args(argv)
    result = verify_project(
        dependencies or default_dependencies(),
        require_source_data=args.require_source_data,
        full=args.full,
    )
    print("\n".join(result.messages))
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())

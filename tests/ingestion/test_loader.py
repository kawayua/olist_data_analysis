from pathlib import Path
from uuid import uuid4

import pandas as pd

from src.config import Settings
from src.database import get_engine, run_sql, run_sql_file
from src.ingestion.contracts import get_contract
from src.ingestion.loader import load_dataset


def test_load_dataset_skips_an_already_loaded_file(tmp_path):
    project_root = Path(__file__).resolve().parents[2]
    engine = get_engine(Settings())
    run_sql_file(
        engine,
        project_root / "sql" / "bootstrap" / "001_schemas.sql",
    )
    run_sql_file(
        engine,
        project_root / "sql" / "bootstrap" / "002_ingestion_runs.sql",
    )
    run_sql(engine, "CREATE SCHEMA IF NOT EXISTS test_raw")
    source_path = tmp_path / "customers.csv"
    unique_customer_id = f"customer-{uuid4()}"
    pd.DataFrame(
        {
            "customer_id": [unique_customer_id],
            "customer_unique_id": ["person-1"],
            "customer_zip_code_prefix": ["10000"],
            "customer_city": ["test-city"],
            "customer_state": ["TS"],
        }
    ).to_csv(source_path, index=False)

    first = load_dataset(
        engine,
        source_path,
        get_contract("customers"),
        schema="test_raw",
    )
    second = load_dataset(
        engine,
        source_path,
        get_contract("customers"),
        schema="test_raw",
    )

    assert first.status == "loaded"
    assert first.row_count == 1
    assert second.status == "skipped"

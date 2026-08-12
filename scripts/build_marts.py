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
    run_sql(engine, "DROP TABLE IF EXISTS marts.customer_segment_strategy")
    run_sql(engine, "DROP TABLE IF EXISTS marts.customer_360")
    run_sql(engine, "DROP TABLE IF EXISTS marts.state_performance")
    run_sql(engine, "DROP TABLE IF EXISTS marts.delivery_order_analysis")
    run_sql(engine, "DROP TABLE IF EXISTS marts.delivery_experience")
    run_sql(engine, "DROP TABLE IF EXISTS marts.product_performance")
    run_sql(engine, "DROP TABLE IF EXISTS marts.repurchase_horizons")
    run_sql(engine, "DROP TABLE IF EXISTS marts.cohort_retention")
    run_sql(engine, "DROP TABLE IF EXISTS marts.monthly_growth")
    for filename in (
        "030_monthly_growth.sql",
        "031_cohort_retention.sql",
        "031_repurchase_horizons.sql",
        "032_customer_360.sql",
        "032_customer_segment_strategy.sql",
        "033_product_performance.sql",
        "034_delivery_experience.sql",
        "035_delivery_order_analysis.sql",
        "036_state_performance.sql",
    ):
        path = PROJECT_ROOT / "sql" / "marts" / filename
        run_sql_file(engine, path)
        print(f"Applied {path.relative_to(PROJECT_ROOT).as_posix()}")


if __name__ == "__main__":
    main()

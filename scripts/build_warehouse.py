"""Rebuild staging and warehouse tables from the immutable raw layer."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DROP_DERIVED_TABLES_SQL = """
DROP TABLE IF EXISTS marts.customer_segment_strategy;
DROP TABLE IF EXISTS marts.ml_customer_features;
DROP TABLE IF EXISTS marts.delivery_rating_analysis;
DROP TABLE IF EXISTS marts.repurchase_intervals;
DROP TABLE IF EXISTS marts.repurchase_behavior;
DROP TABLE IF EXISTS marts.customer_value_analysis;
DROP TABLE IF EXISTS marts.customer_360;
DROP TABLE IF EXISTS marts.state_monthly_performance;
DROP TABLE IF EXISTS marts.state_product_performance;
DROP TABLE IF EXISTS marts.product_monthly_performance;
DROP TABLE IF EXISTS marts.state_performance;
DROP TABLE IF EXISTS marts.delivery_order_analysis;
DROP TABLE IF EXISTS marts.delivery_experience;
DROP TABLE IF EXISTS marts.product_performance;
DROP TABLE IF EXISTS marts.repurchase_horizons;
DROP TABLE IF EXISTS marts.cohort_retention;
DROP TABLE IF EXISTS marts.monthly_growth;
DROP TABLE IF EXISTS warehouse.fact_reviews;
DROP TABLE IF EXISTS warehouse.fact_payments;
DROP TABLE IF EXISTS warehouse.fact_order_items;
DROP TABLE IF EXISTS warehouse.fact_orders;
DROP TABLE IF EXISTS warehouse.dim_date;
DROP TABLE IF EXISTS warehouse.dim_seller;
DROP TABLE IF EXISTS warehouse.dim_product;
DROP TABLE IF EXISTS warehouse.dim_customer;
DROP TABLE IF EXISTS staging.reviews;
DROP TABLE IF EXISTS staging.sellers;
DROP TABLE IF EXISTS staging.products;
DROP TABLE IF EXISTS staging.payments;
DROP TABLE IF EXISTS staging.order_items;
DROP TABLE IF EXISTS staging.orders;
"""


def main() -> None:
    from src.config import get_settings
    from src.database import get_engine, run_sql, run_sql_file

    engine = get_engine(get_settings())
    run_sql(engine, DROP_DERIVED_TABLES_SQL)
    sql_paths = (
        PROJECT_ROOT / "sql" / "staging" / "010_staging.sql",
        PROJECT_ROOT / "sql" / "warehouse" / "020_dimensions.sql",
        PROJECT_ROOT / "sql" / "warehouse" / "021_facts.sql",
    )
    for path in sql_paths:
        run_sql_file(engine, path)
        print(f"Applied {path.relative_to(PROJECT_ROOT).as_posix()}")


if __name__ == "__main__":
    main()

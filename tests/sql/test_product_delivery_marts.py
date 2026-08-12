import subprocess
import sys
from pathlib import Path

from sqlalchemy import text

from src.config import get_settings
from src.database import get_engine


def test_product_and_delivery_marts_have_governed_grains_and_rates():
    project_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "scripts/build_marts.py"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Applied sql/marts/033_product_performance.sql" in result.stdout
    assert "Applied sql/marts/034_delivery_experience.sql" in result.stdout

    engine = get_engine(get_settings())
    with engine.connect() as connection:
        product_rows, product_duplicates, invalid_product_rates = connection.execute(
            text(
                """
                SELECT
                    (SELECT COUNT(*) FROM marts.product_performance),
                    (
                        SELECT COUNT(*) - COUNT(DISTINCT product_category)
                        FROM marts.product_performance
                    ),
                    (
                        SELECT COUNT(*)
                        FROM marts.product_performance
                        WHERE freight_rate_pct < 0
                           OR delayed_delivery_rate_pct < 0
                           OR delayed_delivery_rate_pct > 100
                           OR repurchase_rate_90d_pct < 0
                           OR repurchase_rate_90d_pct > 100
                    )
                """
            )
        ).one()
        delivery_rows, delivery_duplicates, invalid_delivery_rates = connection.execute(
            text(
                """
                SELECT
                    (SELECT COUNT(*) FROM marts.delivery_experience),
                    (
                        SELECT COUNT(*) - COUNT(DISTINCT delivery_status)
                        FROM marts.delivery_experience
                    ),
                    (
                        SELECT COUNT(*)
                        FROM marts.delivery_experience
                        WHERE delayed_delivery_rate_pct < 0
                           OR delayed_delivery_rate_pct > 100
                           OR repurchase_rate_90d_pct < 0
                           OR repurchase_rate_90d_pct > 100
                    )
                """
            )
        ).one()

    assert product_rows > 0
    assert product_duplicates == 0
    assert invalid_product_rates == 0
    assert delivery_rows >= 2
    assert delivery_duplicates == 0
    assert invalid_delivery_rates == 0


def test_delivery_order_analysis_has_one_row_per_delivered_order():
    project_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "scripts/build_marts.py"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Applied sql/marts/035_delivery_order_analysis.sql" in result.stdout

    engine = get_engine(get_settings())
    with engine.connect() as connection:
        actual, expected, duplicates, invalid_statuses, invalid_labels = connection.execute(
            text(
                """
                SELECT
                    (SELECT COUNT(*) FROM marts.delivery_order_analysis),
                    (
                        SELECT COUNT(*)
                        FROM warehouse.fact_orders
                        WHERE order_status = 'delivered'
                    ),
                    (
                        SELECT COUNT(*) - COUNT(DISTINCT order_id)
                        FROM marts.delivery_order_analysis
                    ),
                    (
                        SELECT COUNT(*)
                        FROM marts.delivery_order_analysis
                        WHERE delivery_status NOT IN ('on_time', 'late')
                    ),
                    (
                        SELECT COUNT(*)
                        FROM marts.delivery_order_analysis
                        WHERE (NOT is_first_delivered_order
                            OR NOT COALESCE(eligible_for_90d, false))
                          AND repurchased_within_90d IS NOT NULL
                    )
                """
            )
        ).one()

    assert actual == expected
    assert duplicates == 0
    assert invalid_statuses == 0
    assert invalid_labels == 0

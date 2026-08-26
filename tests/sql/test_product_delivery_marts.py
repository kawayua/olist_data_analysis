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


def test_state_performance_has_one_row_per_customer_state_and_valid_rates():
    project_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "scripts/build_marts.py"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Applied sql/marts/036_state_performance.sql" in result.stdout

    engine = get_engine(get_settings())
    with engine.connect() as connection:
        rows, duplicates, invalid_rates = connection.execute(
            text(
                """
                SELECT
                    (SELECT COUNT(*) FROM marts.state_performance),
                    (
                        SELECT COUNT(*) - COUNT(DISTINCT customer_state)
                        FROM marts.state_performance
                    ),
                    (
                        SELECT COUNT(*)
                        FROM marts.state_performance
                        WHERE delayed_delivery_rate_pct < 0
                           OR delayed_delivery_rate_pct > 100
                           OR repurchase_rate_90d_pct < 0
                           OR repurchase_rate_90d_pct > 100
                    )
                """
            )
        ).one()

    assert rows > 0
    assert duplicates == 0
    assert invalid_rates == 0


def test_state_performance_exposes_delivery_and_review_metrics():
    project_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "scripts/build_marts.py"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    engine = get_engine(get_settings())
    with engine.connect() as connection:
        invalid_states, invalid_buckets = connection.execute(
            text(
                """
                SELECT
                    (
                        SELECT COUNT(*)
                        FROM marts.state_performance
                        WHERE average_delivery_days < 0
                           OR average_review_score NOT BETWEEN 1 AND 5
                    ),
                    (
                        SELECT COUNT(*)
                        FROM marts.delivery_rating_analysis
                        WHERE average_review_score NOT BETWEEN 1 AND 5
                           OR order_count <= 0
                    )
                """
            )
        ).one()

    assert invalid_states == 0
    assert invalid_buckets == 0


def test_state_monthly_performance_has_governed_grain_and_reconciles():
    project_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "scripts/build_marts.py"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Applied sql/marts/040_state_monthly_performance.sql" in result.stdout

    engine = get_engine(get_settings())
    with engine.connect() as connection:
        (
            rows,
            duplicates,
            invalid_aov,
            inconsistent_complete_flags,
            monthly_reconciliation_difference,
            state_reconciliation_difference,
        ) = connection.execute(
            text(
                """
                SELECT
                    (SELECT COUNT(*) FROM marts.state_monthly_performance),
                    (
                        SELECT COUNT(*) - COUNT(DISTINCT (month_start, customer_state))
                        FROM marts.state_monthly_performance
                    ),
                    (
                        SELECT COUNT(*)
                        FROM marts.state_monthly_performance
                        WHERE item_revenue_aov < 0
                           OR payment_aov < 0
                    ),
                    (
                        SELECT COUNT(*)
                        FROM marts.state_monthly_performance AS state_monthly
                        JOIN marts.monthly_growth AS monthly
                            USING (month_start)
                        WHERE state_monthly.is_complete_month
                            IS DISTINCT FROM monthly.is_complete_month
                    ),
                    (
                        SELECT ABS(
                            (SELECT SUM(item_revenue)
                             FROM marts.state_monthly_performance)
                            -
                            (SELECT SUM(item_revenue)
                             FROM marts.monthly_growth)
                        )
                    ),
                    (
                        SELECT ABS(
                            (SELECT SUM(item_revenue)
                             FROM marts.state_monthly_performance)
                            -
                            (SELECT SUM(item_revenue)
                             FROM marts.state_performance)
                        )
                    )
                """
            )
        ).one()

    assert rows > 0
    assert duplicates == 0
    assert invalid_aov == 0
    assert inconsistent_complete_flags == 0
    assert monthly_reconciliation_difference == 0
    assert state_reconciliation_difference == 0


def test_product_performance_exposes_average_review_score():
    project_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "scripts/build_marts.py"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    engine = get_engine(get_settings())
    with engine.connect() as connection:
        invalid = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM marts.product_performance
                WHERE average_review_score NOT BETWEEN 1 AND 5
                """
            )
        ).scalar_one()

    assert invalid == 0


def test_product_monthly_performance_has_one_row_per_month_and_category_and_reconciles():
    project_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "scripts/build_marts.py"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Applied sql/marts/041_product_monthly_performance.sql" in result.stdout

    engine = get_engine(get_settings())
    with engine.connect() as connection:
        rows, duplicates, reconciliation_difference = connection.execute(
            text(
                """
                SELECT
                    (SELECT COUNT(*) FROM marts.product_monthly_performance),
                    (
                        SELECT COUNT(*) - COUNT(DISTINCT (month_start, product_category))
                        FROM marts.product_monthly_performance
                    ),
                    (
                        SELECT ABS(
                            (SELECT SUM(item_revenue)
                             FROM marts.product_monthly_performance)
                            -
                            (SELECT SUM(item_revenue)
                             FROM marts.product_performance)
                        )
                    )
                """
            )
        ).one()

    assert rows > 0
    assert duplicates == 0
    assert reconciliation_difference == 0


def test_state_product_performance_has_governed_grain_and_reconciles():
    project_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "scripts/build_marts.py"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Applied sql/marts/042_state_product_performance.sql" in result.stdout

    engine = get_engine(get_settings())
    with engine.connect() as connection:
        rows, duplicates, reconciliation_difference, sp_rows = connection.execute(
            text(
                """
                SELECT
                    (SELECT COUNT(*) FROM marts.state_product_performance),
                    (
                        SELECT COUNT(*) - COUNT(DISTINCT (customer_state, product_category))
                        FROM marts.state_product_performance
                    ),
                    (
                        SELECT ABS(
                            (SELECT SUM(item_revenue)
                             FROM marts.state_product_performance)
                            -
                            (SELECT SUM(item_revenue)
                             FROM marts.product_performance)
                        )
                    ),
                    (
                        SELECT COUNT(*)
                        FROM marts.state_product_performance
                        WHERE customer_state = 'SP'
                    )
                """
            )
        ).one()

    assert rows > 0
    assert duplicates == 0
    assert reconciliation_difference == 0
    assert sp_rows > 0

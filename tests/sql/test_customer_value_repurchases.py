import subprocess
import sys
from pathlib import Path

from sqlalchemy import text

from src.config import get_settings
from src.database import get_engine


def _rebuild_marts() -> None:
    project_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "scripts/build_marts.py"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_customer_value_analysis_has_one_row_per_segment():
    _rebuild_marts()
    engine = get_engine(get_settings())
    with engine.connect() as connection:
        rows, duplicates = connection.execute(
            text(
                """
                SELECT
                    COUNT(*),
                    COUNT(*) - COUNT(DISTINCT customer_segment)
                FROM marts.customer_value_analysis
                """
            )
        ).one()

    assert rows > 0
    assert duplicates == 0


def test_customer_value_analysis_separates_purchase_stage_revenue():
    _rebuild_marts()
    engine = get_engine(get_settings())
    with engine.connect() as connection:
        columns = set(
            connection.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'marts'
                      AND table_name = 'customer_value_analysis'
                    """
                )
            ).scalars()
        )

    assert {"first_purchase_item_revenue", "repeat_customer_item_revenue"} <= columns


def test_repurchase_behavior_has_exact_horizons_and_interval_buckets():
    _rebuild_marts()
    engine = get_engine(get_settings())
    with engine.connect() as connection:
        horizons = connection.execute(
            text("SELECT DISTINCT horizon_days FROM marts.repurchase_behavior")
        ).scalars().all()
        buckets = connection.execute(
            text("SELECT DISTINCT interval_bucket FROM marts.repurchase_intervals")
        ).scalars().all()

    assert sorted(horizons) == [30, 60, 90]
    assert set(buckets) == {"0_30", "31_60", "61_90", "91_180", "181_plus"}


def test_ml_customer_features_exposes_prediction_audit_columns():
    _rebuild_marts()
    engine = get_engine(get_settings())
    with engine.connect() as connection:
        columns = set(
            connection.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'marts'
                      AND table_name = 'ml_customer_features'
                    """
                )
            ).scalars()
        )

    assert {
        "customer_key",
        "prediction_time",
        "feature_available_at",
        "eligible_for_90d",
        "repurchased_within_90d",
    } <= columns


def test_ml_customer_features_exposes_extended_time_safe_columns():
    """A missing first-order field would weaken ranking without being visible."""
    _rebuild_marts()
    engine = get_engine(get_settings())
    with engine.connect() as connection:
        columns = set(
            connection.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'marts'
                      AND table_name = 'ml_customer_features'
                    """
                )
            ).scalars()
        )

    assert {
        "customer_state",
        "first_order_primary_category",
        "first_order_max_item_revenue",
        "first_order_average_item_revenue",
        "first_order_freight_rate",
        "first_order_payment_type_count",
        "first_order_max_installments",
        "first_order_seller_state_count",
        "first_order_cross_state",
        "first_order_estimated_delivery_days",
        "first_order_delivery_vs_estimate_days",
        "first_order_is_late",
        "first_order_purchase_month",
        "first_order_purchase_weekday",
        "first_order_approval_hours",
        "first_order_carrier_handoff_hours",
    } <= columns


def test_warehouse_rebuilds_when_marts_reference_customer_dimension():
    """Dropping warehouse dimensions before marts leaves rebuilds permanently blocked."""
    project_root = Path(__file__).resolve().parents[2]
    warehouse_result = subprocess.run(
        [sys.executable, "scripts/build_warehouse.py"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert warehouse_result.returncode == 0, warehouse_result.stderr
    marts_result = subprocess.run(
        [sys.executable, "scripts/build_marts.py"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert marts_result.returncode == 0, marts_result.stderr

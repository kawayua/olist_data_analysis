from sqlalchemy import text

from src.config import get_settings
from src.database import get_engine


def test_fact_orders_has_one_row_per_order():
    engine = get_engine(get_settings())

    with engine.connect() as connection:
        result = connection.execute(
            text(
                """
                SELECT COUNT(*) = COUNT(DISTINCT order_id)
                FROM warehouse.fact_orders
                """
            )
        ).scalar_one()

    assert result is True


def test_order_item_revenue_matches_staging():
    engine = get_engine(get_settings())

    with engine.connect() as connection:
        result = connection.execute(
            text(
                """
                SELECT ABS(
                    (SELECT SUM(price) FROM warehouse.fact_order_items)
                    - (SELECT SUM(price) FROM staging.order_items)
                ) < 0.01
                """
            )
        ).scalar_one()

    assert result is True

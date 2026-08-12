"""Compare 90-day repurchase rates for on-time and late first deliveries."""

import json
import sys
from dataclasses import asdict
from pathlib import Path

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analytics.retention import compare_binary_proportions
from src.config import get_settings
from src.database import get_engine


def main() -> None:
    engine = get_engine(get_settings())
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT
                    delivery_status,
                    COUNT(*) AS customers,
                    COUNT(*) FILTER (WHERE repurchased_within_90d) AS repurchased_customers
                FROM marts.delivery_order_analysis
                WHERE is_first_delivered_order
                  AND eligible_for_90d
                GROUP BY delivery_status
                ORDER BY delivery_status
                """
            )
        ).all()

    by_status = {row.delivery_status: row for row in rows}
    on_time = by_status["on_time"]
    late = by_status["late"]
    result = compare_binary_proportions(
        group_zero_successes=int(on_time.repurchased_customers),
        group_zero_total=int(on_time.customers),
        group_one_successes=int(late.repurchased_customers),
        group_one_total=int(late.customers),
    )
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

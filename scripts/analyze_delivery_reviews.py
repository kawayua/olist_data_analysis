"""Compare review-score distributions for on-time and late deliveries."""

import json
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analytics.statistics import compare_binary_groups
from src.config import get_settings
from src.database import get_engine


def main() -> None:
    engine = get_engine(get_settings())
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT review_score, delivery_status
                FROM marts.delivery_order_analysis
                WHERE review_score IS NOT NULL
                ORDER BY order_id
                """
            )
        ).all()

    values = np.array([float(row.review_score) for row in rows])
    groups = np.array([0 if row.delivery_status == "on_time" else 1 for row in rows])
    result = compare_binary_groups(values, groups)
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

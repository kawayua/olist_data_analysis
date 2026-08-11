import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine, text

from src.ingestion.contracts import CONTRACTS


def _scalar(engine: Engine, statement: str) -> int:
    with engine.connect() as connection:
        return int(connection.execute(text(statement)).scalar_one())


def build_quality_report(engine: Engine) -> dict[str, object]:
    tables: dict[str, dict[str, int | float | None]] = {}
    for contract in CONTRACTS.values():
        table_name = f"raw.{contract.name}"
        table_report: dict[str, int | float | None] = {
            "row_count": _scalar(engine, f"SELECT COUNT(*) FROM {table_name}"),
            "duplicate_primary_key_rows": 0,
            "primary_key_missing_rows": None,
        }
        if contract.primary_key:
            primary_key = ", ".join(contract.primary_key)
            table_report["duplicate_primary_key_rows"] = _scalar(
                engine,
                (
                    "SELECT COALESCE(SUM(duplicate_count), 0) FROM ("
                    f"SELECT COUNT(*) AS duplicate_count FROM {table_name} "
                    f"GROUP BY {primary_key} HAVING COUNT(*) > 1"
                    ") duplicates"
                ),
            )
            missing_condition = " OR ".join(
                f"{column} IS NULL" for column in contract.primary_key
            )
            table_report["primary_key_missing_rows"] = _scalar(
                engine,
                f"SELECT COUNT(*) FROM {table_name} WHERE {missing_condition}",
            )
        tables[contract.name] = table_report

    business_checks = {
        "orphan_order_item_orders": _scalar(
            engine,
            """
            SELECT COUNT(*)
            FROM raw.order_items item
            LEFT JOIN raw.orders orders ON item.order_id = orders.order_id
            WHERE orders.order_id IS NULL
            """,
        ),
        "negative_item_prices": _scalar(
            engine,
            "SELECT COUNT(*) FROM raw.order_items WHERE price::NUMERIC < 0",
        ),
        "negative_payment_values": _scalar(
            engine,
            "SELECT COUNT(*) FROM raw.payments WHERE payment_value::NUMERIC < 0",
        ),
        "unknown_order_statuses": _scalar(
            engine,
            """
            SELECT COUNT(*)
            FROM raw.orders
            WHERE order_status NOT IN (
                'created', 'approved', 'invoiced', 'processing', 'shipped',
                'delivered', 'unavailable', 'canceled'
            )
            """,
        ),
        "delivery_before_purchase": _scalar(
            engine,
            """
            SELECT COUNT(*)
            FROM raw.orders
            WHERE order_delivered_customer_date IS NOT NULL
              AND order_purchase_timestamp::TIMESTAMP
                  > order_delivered_customer_date::TIMESTAMP
            """,
        ),
    }
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "tables": tables,
        "business_checks": business_checks,
    }


def write_quality_report(report: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

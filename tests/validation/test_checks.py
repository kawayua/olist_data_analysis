import pandas as pd

from src.ingestion.contracts import get_contract
from src.validation.checks import validate_frame


def test_validation_reports_missing_columns():
    frame = pd.DataFrame({"order_id": ["o1"]})

    report = validate_frame(frame, get_contract("orders"))

    assert "customer_id" in report.missing_columns
    assert report.is_valid is False


def test_validation_reports_duplicate_primary_keys():
    frame = pd.DataFrame(
        {
            "order_id": ["o1", "o1"],
            "customer_id": ["c1", "c1"],
            "order_status": ["delivered", "delivered"],
        }
    )

    report = validate_frame(frame, get_contract("orders"))

    assert report.duplicate_primary_key_rows == 2
    assert report.is_valid is False

from dataclasses import dataclass

import pandas as pd

from src.ingestion.contracts import DatasetContract


@dataclass(frozen=True)
class ValidationReport:
    missing_columns: tuple[str, ...]
    duplicate_primary_key_rows: int

    @property
    def is_valid(self) -> bool:
        return not self.missing_columns and self.duplicate_primary_key_rows == 0


def validate_frame(
    frame: pd.DataFrame,
    contract: DatasetContract,
) -> ValidationReport:
    missing_columns = tuple(sorted(set(contract.columns) - set(frame.columns)))
    duplicate_primary_key_rows = 0
    if contract.primary_key and set(contract.primary_key) <= set(frame.columns):
        primary_key = list(contract.primary_key)
        duplicate_primary_key_rows = int(
            frame.duplicated(primary_key, keep=False).sum()
        )
    return ValidationReport(missing_columns, duplicate_primary_key_rows)

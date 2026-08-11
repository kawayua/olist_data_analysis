from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import pandas as pd
from sqlalchemy import Engine, text

from src.ingestion.contracts import DatasetContract
from src.validation.checks import ValidationReport, validate_frame


@dataclass(frozen=True)
class LoadResult:
    status: str
    source_file: str
    source_hash: str
    row_count: int
    validation: ValidationReport
    error_message: str | None = None


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _record_run(
    engine: Engine,
    *,
    status: str,
    source_file: str,
    source_hash: str,
    row_count: int | None,
    error_message: str | None,
) -> None:
    statement = text(
        """
        INSERT INTO audit.ingestion_runs (
            status, source_file, source_hash, row_count, error_message, finished_at
        ) VALUES (
            :status, :source_file, :source_hash, :row_count, :error_message, NOW()
        )
        """
    )
    with engine.begin() as connection:
        connection.execute(
            statement,
            {
                "status": status,
                "source_file": source_file,
                "source_hash": source_hash,
                "row_count": row_count,
                "error_message": error_message,
            },
        )


def load_dataset(
    engine: Engine,
    path: Path,
    contract: DatasetContract,
    schema: str = "raw",
) -> LoadResult:
    source_file = str(path.resolve())
    source_hash = file_sha256(path)
    frame = pd.read_csv(path, dtype="string")
    validation = validate_frame(frame, contract)

    if not validation.is_valid:
        error_message = "CSV failed structural validation"
        _record_run(
            engine,
            status="failed",
            source_file=source_file,
            source_hash=source_hash,
            row_count=len(frame),
            error_message=error_message,
        )
        return LoadResult(
            status="failed",
            source_file=source_file,
            source_hash=source_hash,
            row_count=len(frame),
            validation=validation,
            error_message=error_message,
        )

    already_loaded = text(
        """
        SELECT EXISTS (
            SELECT 1
            FROM audit.ingestion_runs
            WHERE source_hash = :source_hash AND status = 'completed'
        )
        """
    )
    completed_run = text(
        """
        INSERT INTO audit.ingestion_runs (
            status, source_file, source_hash, row_count, finished_at
        ) VALUES ('completed', :source_file, :source_hash, :row_count, NOW())
        """
    )
    with engine.begin() as connection:
        is_loaded = connection.execute(
            already_loaded, {"source_hash": source_hash}
        ).scalar_one()
        if is_loaded:
            return LoadResult(
                status="skipped",
                source_file=source_file,
                source_hash=source_hash,
                row_count=len(frame),
                validation=validation,
            )

        frame.to_sql(
            contract.name,
            connection,
            schema=schema,
            if_exists="replace",
            index=False,
            method="multi",
            chunksize=1_000,
        )
        connection.execute(
            completed_run,
            {"source_file": source_file, "source_hash": source_hash, "row_count": len(frame)},
        )
    return LoadResult(
        status="loaded",
        source_file=source_file,
        source_hash=source_hash,
        row_count=len(frame),
        validation=validation,
    )

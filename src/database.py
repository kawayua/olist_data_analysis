from pathlib import Path

from sqlalchemy import Engine, create_engine

from src.config import Settings


def get_engine(settings: Settings) -> Engine:
    """Build a database engine from typed application settings."""
    return create_engine(settings.database_url, pool_pre_ping=True)


def run_sql(engine: Engine, statement: str) -> None:
    """Execute one SQL statement atomically."""
    with engine.begin() as connection:
        connection.exec_driver_sql(statement)


def run_sql_file(engine: Engine, path: Path) -> None:
    """Run the SQL stored in one UTF-8 text file."""
    run_sql(engine, path.read_text(encoding="utf-8"))

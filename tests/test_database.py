import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

from src.config import Settings
from src.database import get_engine, run_sql, run_sql_file


def test_run_sql_executes_inside_transaction():
    engine = create_engine("sqlite+pysqlite:///:memory:")

    run_sql(engine, "create table example (id integer primary key)")

    with engine.connect() as connection:
        result = connection.execute(text("select count(*) from example"))
        assert result.scalar_one() == 0


def test_get_engine_uses_settings_database_url():
    settings = Settings(postgres_host="database.example")

    engine = get_engine(settings)

    assert str(engine.url.host) == "database.example"


def test_run_sql_file_executes_file_contents(tmp_path):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    path = tmp_path / "create_example.sql"
    path.write_text("create table example (id integer primary key)", encoding="utf-8")

    run_sql_file(engine, path)

    with engine.connect() as connection:
        assert connection.execute(text("select count(*) from example")).scalar_one() == 0


def test_bootstrap_script_runs_directly_from_project_root():
    project_root = Path(__file__).resolve().parents[1]

    result = subprocess.run(
        [sys.executable, "scripts/bootstrap_db.py"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Applied sql/bootstrap/001_schemas.sql" in result.stdout

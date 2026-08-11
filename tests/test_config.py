from src.config import Settings


def test_database_url_is_built_from_components():
    settings = Settings(
        postgres_user="analytics",
        postgres_password="secret",
        postgres_host="db",
        postgres_port=5432,
        postgres_db="olist",
        llm_api_key="",
        llm_base_url="https://example.invalid/v1",
        llm_model="demo",
    )

    assert settings.database_url == (
        "postgresql+psycopg://analytics:secret@db:5432/olist"
    )

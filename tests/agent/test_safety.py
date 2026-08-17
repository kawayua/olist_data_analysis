import pytest

from src.agent.safety import UnsafeQueryError, validate_read_only_sql

ALLOWED_VIEWS = {"marts.monthly_growth", "marts.customer_360"}


def test_allowed_select_receives_default_limit():
    actual = validate_read_only_sql(
        "select month_start from marts.monthly_growth", ALLOWED_VIEWS
    )

    assert "LIMIT 500" in actual.upper()


@pytest.mark.parametrize(
    "sql",
    [
        "delete from marts.monthly_growth",
        "create table marts.bad as select * from marts.monthly_growth",
        "select 1; drop table warehouse.fact_orders",
        "select * from raw.orders",
        "select * from monthly_growth",
        "select * from marts.monthly_growth limit 0",
        "select * from marts.monthly_growth limit 2001",
        "select * from marts.monthly_growth limit '500'",
        "with safe as (select * from marts.customer_360), unsafe as (select * from raw.orders) select * from safe",
        "with removed as (delete from marts.customer_360 returning *) select * from removed",
        "select * into marts.exported_growth from marts.monthly_growth",
        "select * from marts.monthly_growth for update",
    ],
)
def test_unsafe_or_unbounded_sql_is_rejected(sql):
    with pytest.raises(UnsafeQueryError):
        validate_read_only_sql(sql, ALLOWED_VIEWS)


def test_error_does_not_echo_raw_query_or_credentials():
    secret = "postgresql://user:password@example.invalid/database"

    with pytest.raises(UnsafeQueryError) as error:
        validate_read_only_sql(f"select * from raw.orders -- {secret}", ALLOWED_VIEWS)

    assert secret not in str(error.value)

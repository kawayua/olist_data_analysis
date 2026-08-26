import pytest

from src.agent.safety import UnsafeQueryError, validate_read_only_sql

ALLOWED_VIEWS = {"marts.monthly_growth", "marts.customer_360"}


def test_allowed_select_receives_default_limit():
    actual = validate_read_only_sql(
        "select month_start from marts.monthly_growth", ALLOWED_VIEWS
    )

    assert "LIMIT 500" in actual.upper()


def test_safe_sql_allows_monthly_category_trend_filters_with_and():
    sql = """
        SELECT month_start, item_revenue
        FROM marts.product_monthly_performance
        WHERE product_category = 'health_beauty'
          AND month_start >= DATE '2017-01-01'
          AND month_start < DATE '2018-01-01'
        ORDER BY month_start
    """

    normalized = validate_read_only_sql(
        sql, {"marts.product_monthly_performance"}
    )

    assert "product_category = 'health_beauty'" in normalized
    assert "ORDER BY month_start" in normalized


def test_allowed_union_all_receives_default_limit():
    actual = validate_read_only_sql(
        "select month_start from marts.monthly_growth "
        "union all select customer_unique_id from marts.customer_360",
        ALLOWED_VIEWS,
    )

    assert "UNION ALL" in actual.upper()
    assert "LIMIT 500" in actual.upper()


def test_standard_analytical_aggregate_and_scalar_functions_are_allowed():
    actual = validate_read_only_sql(
        "select date_trunc('month', month_start), count(*), "
        "round(avg(order_count), 2), coalesce(max(revenue), 0) "
        "from marts.monthly_growth group by 1",
        ALLOWED_VIEWS,
    )

    assert "COUNT(*)" in actual.upper()
    assert "COALESCE" in actual.upper()


@pytest.mark.parametrize(
    "sql",
    [
        "select pg_sleep(4) from marts.monthly_growth limit 1",
        "select current_user",
        "select current_database() from marts.monthly_growth",
        "select random() from marts.monthly_growth",
        "select * from generate_series(1, 10)",
    ],
)
def test_system_dangerous_or_table_valued_functions_are_rejected(sql):
    with pytest.raises(UnsafeQueryError):
        validate_read_only_sql(sql, ALLOWED_VIEWS)


@pytest.mark.parametrize(
    "sql",
    [
        (
            "with oversized as (select * from marts.monthly_growth limit 2001) "
            "select * from oversized"
        ),
        (
            "(select * from marts.monthly_growth limit 2001) union all "
            "(select * from marts.customer_360)"
        ),
    ],
)
def test_nested_or_set_operand_limit_cannot_bypass_cap(sql):
    with pytest.raises(UnsafeQueryError):
        validate_read_only_sql(sql, ALLOWED_VIEWS)


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

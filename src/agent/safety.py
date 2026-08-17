"""AST-based guardrails for read-only analytical SQL."""

from __future__ import annotations

import sqlglot
from sqlglot import exp

DEFAULT_LIMIT = 500
MAX_LIMIT = 2_000

# The SQL tool is for compact mart analytics, not arbitrary PostgreSQL execution.
# These deterministic aggregate/scalar functions cover grouping, date bucketing,
# formatting, and arithmetic while excluding system, volatile, and I/O functions.
ALLOWED_FUNCTIONS = {
    "ABS",
    "AVG",
    "CAST",
    "CEIL",
    "CEILING",
    "COALESCE",
    "CONCAT",
    "COUNT",
    "DATE",
    "DATE_ADD",
    "DATE_DIFF",
    "EXTRACT",
    "FLOOR",
    "GREATEST",
    "LEAST",
    "LENGTH",
    "LOWER",
    "MAX",
    "MIN",
    "MOD",
    "NULLIF",
    "POWER",
    "REPLACE",
    "ROUND",
    "SPLIT_PART",
    "SQRT",
    "STRING_AGG",
    "SUBSTRING",
    "SUM",
    "TIMESTAMP_TRUNC",
    "TRIM",
    "UPPER",
}


class UnsafeQueryError(ValueError):
    """Raised when a query exceeds the analytical read-only boundary."""


def _raise_unsafe(message: str) -> None:
    raise UnsafeQueryError(message)


def _cte_names(expression: exp.Expression) -> set[str]:
    return {
        cte.alias_or_name.lower()
        for cte in expression.find_all(exp.CTE)
        if cte.alias_or_name
    }


def _validate_read_only_nodes(expression: exp.Expression) -> None:
    mutating_node_types = (exp.DML, exp.DDL, exp.Command, exp.Transaction)
    if any(isinstance(node, mutating_node_types) for node in expression.walk()):
        _raise_unsafe("only one read-only SELECT statement is allowed")

    for select in expression.find_all(exp.Select):
        if select.args.get("into") or select.args.get("locks"):
            _raise_unsafe("only one read-only SELECT statement is allowed")


def _validate_tables(expression: exp.Expression, allowed_views: set[str]) -> None:
    cte_names = _cte_names(expression)
    normalized_allowed_views = {view.lower() for view in allowed_views}
    allowed_source_count = 0

    for table in expression.find_all(exp.Table):
        if table.catalog or not table.db:
            if table.name.lower() in cte_names and not table.catalog and not table.db:
                continue
            _raise_unsafe("query references a non-governed view")

        qualified_name = f"{table.db}.{table.name}".lower()
        if qualified_name not in normalized_allowed_views:
            _raise_unsafe("query references a non-governed view")
        allowed_source_count += 1

    if allowed_source_count == 0:
        _raise_unsafe("query must read from a governed view")


def _validate_functions(expression: exp.Expression) -> None:
    for function in expression.find_all(exp.Func):
        if function.sql_name().upper() not in ALLOWED_FUNCTIONS:
            _raise_unsafe("query uses a non-analytical function")


def _validate_limit_value(limit: exp.Limit) -> None:
    value = limit.expression
    if not isinstance(value, exp.Literal) or not value.is_int:
        _raise_unsafe("query limit must be a positive integer")

    limit_value = int(value.this)
    if limit_value <= 0 or limit_value > MAX_LIMIT:
        _raise_unsafe("query limit is outside the permitted range")


def _validated_limit(expression: exp.Select | exp.SetOperation) -> None:
    for limit in expression.find_all(exp.Limit):
        _validate_limit_value(limit)

    if expression.args.get("limit") is None:
        expression.set("limit", exp.Limit(expression=exp.Literal.number(DEFAULT_LIMIT)))


def validate_read_only_sql(sql: str, allowed_views: set[str]) -> str:
    """Return a normalized, bounded SELECT statement or raise ``UnsafeQueryError``."""
    if not sql or not sql.strip():
        _raise_unsafe("only one read-only SELECT statement is allowed")

    try:
        expressions = [
            expression for expression in sqlglot.parse(sql, read="postgres") if expression
        ]
    except sqlglot.errors.ParseError:
        _raise_unsafe("only one read-only SELECT statement is allowed")

    if len(expressions) != 1 or not isinstance(
        expressions[0], (exp.Select, exp.SetOperation)
    ):
        _raise_unsafe("only one read-only SELECT statement is allowed")

    expression = expressions[0]
    _validate_read_only_nodes(expression)
    _validate_tables(expression, allowed_views)
    _validate_functions(expression)
    _validated_limit(expression)
    return expression.sql(dialect="postgres")

import pandas as pd


def eligible_for_horizon(
    first_purchase: pd.Timestamp,
    data_end: pd.Timestamp,
    days: int,
) -> bool:
    """Return whether a customer has a complete post-purchase observation window."""
    return data_end >= first_purchase + pd.Timedelta(days=days)

import pandas as pd


def ActionDataFrame():
    """
    Creates an empty DataFrame with predefined columns for user actions.

    Returns:
        DataFrame: An empty DataFrame with the specified columns.
    """
    return pd.DataFrame(columns=["country", "language", "platform", "values", "rev_date", "slug", "experiment_slug", "is_latest_rev"])
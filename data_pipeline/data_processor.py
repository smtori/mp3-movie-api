import logging
import pandas as pd

logger = logging.getLogger(__name__)


def remove_duplicates(df):
    """Remove duplicate rows."""
    df_orig_len = len(df)
    df = df.drop_duplicates()

    logger.debug(f"{df_orig_len - len(df)} duplicate row(s) removed.")
    return df


def handle_missing(df, axis="rows"):
    """Drop rows or columns containing missing values."""
    ax = 1 if axis == "columns" else 0
    label = "columns" if ax == 1 else "row"

    before = df.shape[ax]
    df = df.dropna(axis=ax)

    logger.debug(f"{before-df.shape[ax]} null {label}(s) removed.")

    return df


def remove_outliers(df, columns, method, threshold):
    """Remove outliers from the specified numeric columns."""
    if method not in ("iqr", "zscore"):
        logger.error(f"Unsupported method: {method}")
        raise ValueError("Method must be 'iqr' or 'zscore'.")

    before = len(df)

    for column in columns:
        if column not in df.columns:
            logger.warning(f"Column {column} not found.")
            continue
        if not pd.api.types.is_numeric_dtype(df[column]):
            logger.warning(f"Column {column} is not numeric.")
            continue

        if method == "iqr":
            q1 = df[column].quantile(0.25)
            q3 = df[column].quantile(0.75)
            iqr = q3 - q1
            lower = q1 - threshold * iqr
            upper = q3 + threshold * iqr
            df = df[(df[column] >= lower) & (df[column] <= upper)]
        else:
            zscore = ((df[column] - df[column].mean()) / df[column].std()).abs()
            df = df[zscore < threshold]

    logger.debug(f"Method={method}, threshold={threshold}: {before - len(df)} row(s) removed.")

    return df


def process_data(df, config):
    """Apply the processing steps enabled in the configuration."""
    steps = config["processing"]

    if steps["remove_duplicates"]:
        df = remove_duplicates(df)

    missing = steps["missing"]
    if missing["enabled"]:
        df = handle_missing(df, missing["axis"])

    outliers = steps["outliers"]
    if outliers["enabled"]:
        df = remove_outliers(
            df,
            outliers["columns"],
            outliers["method"],
            outliers["threshold"],
        )

    return df


def create_cleaning_report(df_before, df_after):
    """Return a dictionary summarizing the cleaning results."""
    cleaning_report = {
        'rows_before': df_before.shape[0],
        'rows_after': df_after.shape[0],
        'rows_removed': df_before.shape[0] - df_after.shape[0],
        'columns_before': df_before.shape[1],
        'columns_after': df_after.shape[1],
        'columns_removed': df_before.shape[1] - df_after.shape[1]
    }

    return cleaning_report


import logging
import pandas as pd

logger = logging.getLogger(__name__)


def validate_dataframe(df, required_columns, numeric_columns):
    """Validate the Dataframe and return the valid data.

    required_columns: a list of column names that must exist.
    numeric_columns: a list of column names whose values should
    be numeric.
    """
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        logger.error("Missing required columns: %s", missing)
        raise ValueError(f"Missing required columns: {missing}")

    # Make copy
    df = df.copy()
    original_count = len(df)

    for col in numeric_columns:
        invalid_rows = []
        for i, value in df[col].items():
            if pd.notna(value):
                try:
                    float(value)
                except ValueError:
                    logger.warning(f"{col} contains invalid values at row {i}")
                    invalid_rows.append(i)
        if invalid_rows:
            df = df.drop(index=invalid_rows)

        df[col] = pd.to_numeric(df[col])

    valid_count = len(df)
    removed_count = original_count - valid_count

    # Log count
    logger.debug(f"Valid Rows: {valid_count}")
    logger.debug(f"Removed Rows: {removed_count}")

    return df

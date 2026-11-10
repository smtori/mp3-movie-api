import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def save_data(df, filepath):
    """Save a DataFrame as a CSV file."""
    output_path = Path(filepath)

    # Create the output directory
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save the DataFrame as CSV without the index.
    df.to_csv(output_path, index=False)

    logger.debug(f"Saved {len(df)} rows to {output_path}")

    return output_path

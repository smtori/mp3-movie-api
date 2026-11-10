import io
import logging
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile

from src import (
    HealthResponse,
    setup_logging,
    ProcessConfig,
    log_requests,
    MovieStorage,
    MovieUploadInfo,
    MovieDataResponse,
    MovieProcessingReport,
)
from src.storage import MOVIE_COLUMNS

from data_pipeline import (
    create_cleaning_report,
    process_data,
    validate_dataframe,
)

setup_logging(verbose=True)
logger = logging.getLogger(__name__)

app = FastAPI(title="Data Processing API", version="1.0.0")
app.middleware("http")(log_requests)
storage = MovieStorage()


@app.get("/health", response_model=HealthResponse)
def health_check():
    """Return the application status and version."""
    return {"status": "ok", "version": "1.0.0"}


@app.post("/upload", response_model=MovieUploadInfo)
async def upload_movies(file: UploadFile = File(...)):
    """Read a CSV upload and replace the stored movie collection."""
    filename = file.filename or ""

    # Accept CSV files only
    suffix = Path(filename).suffix.lower()
    if suffix != ".csv":
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Please upload a .csv file.",
        )

    contents = await file.read()

    try:
        df = pd.read_csv(io.BytesIO(contents))
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as e:
        logger.warning("Failed to parse uploaded file %s: %s", filename, e)
        raise HTTPException(
            status_code=400,
            detail="Could not read the file.",
        )

    # Quick validation before saving
    if len(df.columns) != len(MOVIE_COLUMNS) or set(df.columns) != set(MOVIE_COLUMNS):
        raise HTTPException(
            status_code=400,
            detail=f"CSV must contain exactly these columns: {MOVIE_COLUMNS}",
        )
    if df.empty:
        raise HTTPException(
            status_code=400,
            detail="CSV must contain at least one data row.",
        )

    # Reorder columns so they line up with the INSERT statement
    df = df[MOVIE_COLUMNS]

    storage.save(df)
    logger.info("Uploaded movies: filename=%s, rows=%d", filename, len(df))

    return MovieUploadInfo(
        filename=filename,
        rows=len(df),
        columns=len(df.columns),
        column_names=list(df.columns),
    )


@app.get("/movies", response_model=MovieDataResponse)
def get_movies(limit: int = Query(default=100, ge=1)):
    """Return up to limit stored movies and the total count."""
    total_rows = storage.count_movies()
    if total_rows == 0:
        return {"data": [], "total_rows": 0}

    data = storage.select_columns(MOVIE_COLUMNS, limit)

    logger.info("Returned %d rows from movies", len(data))
    return {"data": data, "total_rows": total_rows}


@app.get("/movies/search", response_model=list[dict])
def query_movies(
    columns: list[str] = Query(default=["title"]),
    min_rating: float = Query(default=0, ge=0, le=10),
    limit: int = Query(default=100, ge=1),
):
    """Return selected fields from movies at or above a minimum rating."""
    try:
        results = storage.query_movies(columns, min_rating, limit)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    logger.info(
        "Queried movies: columns=%s, min_rating=%s, returned_rows=%d",
        columns,
        min_rating,
        len(results),
    )
    return results


@app.post("/movies/process", response_model=MovieProcessingReport)
def process_movies(config: ProcessConfig):
    """Validate and process the stored movies using MP1 functions."""
    df = storage.get()
    if df.empty:
        raise HTTPException(status_code=400, detail="No movies stored. Upload a CSV first.")

    # Request model
    config_dict = config.model_dump()
    required_columns = config_dict["validation"]["required_columns"]
    numeric_columns = config_dict["validation"]["numeric_columns"]

    missing_numeric = [col for col in numeric_columns if col not in df.columns]
    if missing_numeric:
        raise HTTPException(
            status_code=400,
            detail=f"Numeric columns not found in dataset: {missing_numeric}",
        )

    try:
        rows_before_validation = len(df)
        validated_df = validate_dataframe(
            df,
            required_columns=required_columns,
            numeric_columns=numeric_columns,
        )
        validation_rows_removed = rows_before_validation - len(validated_df)

        # Copy before processing
        validated_copy = validated_df.copy()

        processed_df = process_data(validated_df, config_dict)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    cleaning_report = create_cleaning_report(validated_copy, processed_df)

    # Replace the stored collection with the processed data
    storage.save(processed_df)

    logger.info(
        "Processed movies: validation_removed=%d, rows_before=%d, rows_after=%d",
        validation_rows_removed,
        cleaning_report["rows_before"],
        cleaning_report["rows_after"],
    )

    return {
        "validation_rows_removed": validation_rows_removed,
        "cleaning_report": cleaning_report,
    }
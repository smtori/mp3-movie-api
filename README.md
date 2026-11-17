# mp3-movie-api

# mp3-movie-api

This project is a FastAPI service that stores a single movie collection in SQLite, cleans it with the MP1 data pipeline, and caches repeated retrievals. `main.py` defines the endpoints, while the `src/` package holds the request/response models, logging middleware, the SQLite connection and table setup (`database.py`), the SQL-based `MovieStorage` class (`storage.py`), and the FakeRedis-backed `MovieCache` (`cache.py`). The `data_pipeline/` package contains the reused MP1 validation and cleaning functions. `POST /upload` checks that a CSV has exactly the columns `title`, `release_year`, `rating`, and `genre`, then replaces every stored row in one SQLite transaction, so the data survives server restarts. `GET /movies` returns up to `limit` rows plus the total count, and `GET /movies/search` filters and sorts by rating using SQL. `POST /movies/process` loads the stored rows into a DataFrame, validates and cleans them according to the request settings, and saves the result back to the database. Only `GET /movies` is cached, with one entry per `limit` that expires after 90 seconds. Every successful upload or processing run clears the whole cache so clients never receive outdated rows.

## Running

```bash
python -m uvicorn main:app --reload
python -m pytest tests -v
```

## Sample processing request

After uploading `fixtures/sample_movies.csv`, send `POST /movies/process` with:

```json
{
  "validation": {
    "required_columns": ["title", "release_year", "rating", "genre"],
    "numeric_columns": ["release_year", "rating"]
  },
  "processing": {
    "remove_duplicates": true,
    "missing": {"enabled": true, "axis": "rows"},
    "outliers": {"enabled": true, "columns": ["rating"], "method": "iqr", "threshold": 1.5}
  }
}
```

Expected response:

```json
{
  "validation_rows_removed": 0,
  "cleaning_report": {
    "rows_before": 20,
    "rows_after": 16,
    "rows_removed": 4,
    "columns_before": 4,
    "columns_after": 4,
    "columns_removed": 0
  }
}
```

from pathlib import Path

import pandas as pd
import pytest

from src import MovieStorage
from src.storage import MOVIE_COLUMNS
import main


def test_movies_persist(client, test_storage, uploaded_movies):
    reopened = MovieStorage(test_storage.db_path)

    df = reopened.get()
    assert len(df) == 20
    assert reopened.count_movies() == 20
    assert list(df.columns) == MOVIE_COLUMNS

    original = pd.read_csv(Path("fixtures") / "sample_movies.csv")
    assert df["title"].fillna("").tolist() == original["title"].fillna("").tolist()

    db_ids = [row["id"] for row in reopened.select_columns(MOVIE_COLUMNS, 100)]

    response = client.get("/movies", params={"limit": 100})
    assert response.status_code == 200
    api_ids = [row["id"] for row in response.json()["data"]]

    assert db_ids == list(range(1, 21))
    assert api_ids == db_ids


def test_cache_and_processing(client, uploaded_movies, processing_body):
    first_bodies = {}
    for limit in (100, 1):
        response = client.get("/movies", params={"limit": limit})
        assert response.status_code == 200
        assert main.cache.get(limit) == response.json()
        first_bodies[limit] = response.json()

    repeat = client.get("/movies", params={"limit": 100})
    assert repeat.status_code == 200
    assert repeat.json() == first_bodies[100]

    response = client.post("/movies/process", json=processing_body)
    assert response.status_code == 200
    report = response.json()
    assert report["validation_rows_removed"] == 0
    assert report["cleaning_report"] == {
        "rows_before": 20,
        "rows_after": 16,
        "rows_removed": 4,
        "columns_before": 4,
        "columns_after": 4,
        "columns_removed": 0,
    }
    assert main.cache.get(100) is None
    assert main.cache.get(1) is None

    response = client.get("/movies", params={"limit": 100})
    assert response.status_code == 200
    body = response.json()

    assert body["total_rows"] == 16
    assert len(body["data"]) == 16
    expected_titles = [f"Movie {letter}" for letter in "ABCDEFGHIJKLMNOP"]
    assert [movie["title"] for movie in body["data"]] == expected_titles
    assert [movie["id"] for movie in body["data"]] == list(range(1, 17))
    assert main.cache.get(100) == body


def test_cache_hit_skips_database(client, uploaded_movies, monkeypatch):
    first = client.get("/movies", params={"limit": 100})
    assert first.status_code == 200

    def fail_if_called(*args, **kwargs):
        pytest.fail("Database was queried even though the response was cached")

    monkeypatch.setattr(main.storage, "select_columns", fail_if_called)
    monkeypatch.setattr(main.storage, "count_movies", fail_if_called)

    second = client.get("/movies", params={"limit": 100})
    assert second.status_code == 200
    assert second.json() == first.json()

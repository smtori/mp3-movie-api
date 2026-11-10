import logging
import sqlite3

import pandas as pd

from .database import get_connection, initialize_database

logger = logging.getLogger(__name__)
MOVIE_COLUMNS = ["title", "release_year", "rating", "genre"]


class MovieStorage:
    def __init__(self, db_path="data/movies.db"):
        self.db_path = db_path
        initialize_database(self.db_path)

    def save(self, df):
        """Replace all movie rows in one transaction."""
        clean = df.astype(object).where(df.notna(), None)
        rows = list(clean.itertuples(index=False, name=None))

        connection = get_connection(self.db_path)

        try:
            # Delete all old rows
            connection.execute("DELETE FROM movies")

            # Insert all new rows
            connection.executemany(
                "INSERT INTO movies (title, release_year, rating, genre) VALUES (?, ?, ?, ?)",
                rows,
            )
            # commit
            connection.commit()
            # log at debug
            logger.debug(f"Stored movies in SQLite: rows={len(rows)}")
        finally:
            connection.close()

        def get(self):
            """Return the four movie columns as a DataFrame, ordered by id."""
            query = "SELECT title, release_year, rating, genre FROM movies ORDER BY id"
            connection = get_connection(self.db_path)
            try:
                rows = connection.execute(query).fetchall()
            finally:
                connection.close()

            return pd.DataFrame([tuple(row) for row in rows], columns=MOVIE_COLUMNS)

    def select_columns(self, columns, limit=5):
        """Return id plus the requested movie columns, ordered by id."""
        if not columns:
            logger.error("Select at least one column")
            raise ValueError("Select at least one column")

        for column in columns:
            if column not in MOVIE_COLUMNS:
                logger.error(f"Unsupported column: {column}")
                raise ValueError(f"Unsupported column: {column}")

        selected_columns = ", ".join(["id"] + columns)
        connection = get_connection(self.db_path)
        try:
            query = f"SELECT {selected_columns} FROM movies ORDER BY id LIMIT ?"
            rows = connection.execute(query, (limit,)).fetchall()

            result = [dict(row) for row in rows]
            logger.debug(f"Selected columns={columns}, rows={len(result)}")
            return result
        finally:
            connection.close()

    def count_movies(self):
        """Return the number of stored movies using SQL COUNT(*)."""
        connection = get_connection(self.db_path)
        try:
            return connection.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
        finally:
            connection.close()

    def query_movies(self, columns, min_rating, limit):
        """Return selected fields from matching movies using SQL."""
        if not columns:
            logger.error("Select at least one column")
            raise ValueError("Select at least one column")

        for column in columns:
            if column not in MOVIE_COLUMNS:
                logger.error(f"Unsupported column: {column}")
                raise ValueError(f"Unsupported column: {column}")

        selected_columns = ", ".join(["id"] + columns)
        connection = get_connection(self.db_path)

        try:
            query = f"SELECT {selected_columns} FROM movies WHERE rating >= ? ORDER BY rating DESC, id ASC LIMIT ?"
            rows = connection.execute(query, (min_rating, limit)).fetchall()

            # Return dictionaries and log the selected columns and row count at DEBUG.
            result = [dict(row) for row in rows]
            logger.debug(
                f"Queried movies: columns={columns}, min_rating={min_rating}, "
                f"returned_rows={len(result)}"
            )

            return result
        finally:
            connection.close()

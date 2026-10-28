# src/api/database.py

import os
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATABASE_PATH = Path(
    os.getenv(
        "DB_PATH",
        str(PROJECT_ROOT / "databases" / "books_database.db")
    )
)


def get_stats():
    """Return statistics about the books stored in SQLite."""

    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DATABASE_PATH}"
        )

    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row

        total_books = conn.execute(
            "SELECT COUNT(*) FROM books"
        ).fetchone()[0]

        books_with_descriptions = conn.execute(
            """
            SELECT COUNT(*)
            FROM books
            WHERE description IS NOT NULL
              AND TRIM(description) != ''
            """
        ).fetchone()[0]

        books_with_subjects = conn.execute(
            """
            SELECT COUNT(*)
            FROM books
            WHERE subjects IS NOT NULL
              AND TRIM(subjects) != ''
            """
        ).fetchone()[0]

        # Count authors using the current normalized schema.
        unique_authors = conn.execute(
            """
            SELECT COUNT(DISTINCT a.author_id)
            FROM authors AS a
            INNER JOIN books AS b
                ON b.author_id = a.author_id
            """
        ).fetchone()[0]

        year_rows = conn.execute(
            """
            SELECT "year-of-publication" AS year,
                   COUNT(*) AS count
            FROM books
            WHERE "year-of-publication" IS NOT NULL
            GROUP BY "year-of-publication"
            ORDER BY "year-of-publication" DESC
            LIMIT 10
            """
        ).fetchall()

    return {
        "database": DATABASE_PATH.name,
        "total_books": total_books,
        "books_with_descriptions": books_with_descriptions,
        "books_with_subjects": books_with_subjects,
        "unique_authors": unique_authors,
        "top_10_publication_years": [
            {"year": row["year"], "count": row["count"]}
            for row in year_rows
        ],
    }

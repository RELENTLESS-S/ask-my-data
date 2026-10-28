
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "databases" / "books_database.db"


def migrate_database():
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DATABASE_PATH}"
        )

    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        # Prevent accidentally migrating an already migrated database.
        tables = {
            row[0]
            for row in conn.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
            """)
        }

        if "authors" in tables:
            raise RuntimeError(
                "An authors table already exists. "
                "Inspect the schema before running this migration again."
            )

        columns = {
            row[1]
            for row in conn.execute('PRAGMA table_info("books")')
        }

        required_columns = {
            "isbn",
            "book-title",
            "book-author",
            "year-of-publication",
            "publisher",
            "description",
            "subjects",
        }

        if not required_columns.issubset(columns):
            raise RuntimeError(
                f"Unexpected books schema. Found columns: {columns}"
            )

        # Create the authors table.
        conn.execute("""
            CREATE TABLE authors (
                author_id INTEGER PRIMARY KEY,
                author_name TEXT NOT NULL UNIQUE
            )
        """)

        # Extract unique, non-empty author names from existing books.
        conn.execute("""
            INSERT INTO authors (author_name)
            SELECT DISTINCT TRIM("book-author")
            FROM books
            WHERE "book-author" IS NOT NULL
              AND TRIM("book-author") != ''
            ORDER BY TRIM("book-author")
        """)

        # Create a normalized books table with a primary key
        # and a foreign key referencing authors.
        conn.execute("""
            CREATE TABLE books_new (
                book_id INTEGER PRIMARY KEY,
                isbn TEXT,
                "book-title" TEXT,
                author_id INTEGER,
                "year-of-publication" INTEGER,
                publisher TEXT,
                description TEXT,
                subjects TEXT,
                FOREIGN KEY (author_id)
                    REFERENCES authors(author_id)
            )
        """)

        # Copy all existing books and link each to its author.
        # Books with missing author names get author_id = NULL.
        conn.execute("""
            INSERT INTO books_new (
                isbn,
                "book-title",
                author_id,
                "year-of-publication",
                publisher,
                description,
                subjects
            )
            SELECT
                b.isbn,
                b."book-title",
                a.author_id,
                b."year-of-publication",
                b.publisher,
                b.description,
                b.subjects
            FROM books AS b
            LEFT JOIN authors AS a
                ON TRIM(b."book-author") = a.author_name
        """)

        old_count = conn.execute(
            "SELECT COUNT(*) FROM books"
        ).fetchone()[0]

        new_count = conn.execute(
            "SELECT COUNT(*) FROM books_new"
        ).fetchone()[0]

        if old_count != new_count:
            raise RuntimeError(
                f"Book count mismatch: {old_count} vs {new_count}"
            )

        # Replace the original table only after the copy succeeds.
        conn.execute("DROP TABLE books")
        conn.execute("ALTER TABLE books_new RENAME TO books")

        # Verify referential integrity before committing.
        violations = conn.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if violations:
            raise RuntimeError(
                f"Foreign key violations found: {violations}"
            )

        author_count = conn.execute(
            "SELECT COUNT(*) FROM authors"
        ).fetchone()[0]

        final_count = conn.execute(
            "SELECT COUNT(*) FROM books"
        ).fetchone()[0]

    print("Migration successful!")
    print(f"Books preserved: {final_count}")
    print(f"Unique authors created: {author_count}")
    print("Foreign key check passed.")


if __name__ == "__main__":
    migrate_database()

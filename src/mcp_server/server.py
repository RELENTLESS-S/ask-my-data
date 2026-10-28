
from pathlib import Path
from contextlib import contextmanager
from typing import Any, Literal, Annotated
import logging
import sqlite3

import chromadb
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction
from fastmcp import FastMCP
from pydantic import Field


# ============================================================
# 1. PROJECT CONFIGURATION
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[2]

DB_PATH = ROOT_DIR / "databases" / "books_database.db"
CHROMA_PATH = ROOT_DIR / "chroma_db"

COLLECTION_NAME = "books_semantic"
EMBEDDING_MODEL = "nomic-embed-text"
OLLAMA_EMBEDDING_URL = "http://localhost:11434/api/embeddings"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("Ask My Data Books")

_collection = None


# ============================================================
# 2. CHROMADB CONNECTION
# ============================================================

def get_collection():
    """
    Connect to the existing persistent ChromaDB collection.
    This function does not re-index the books.
    """
    global _collection

    if _collection is None:
        if not CHROMA_PATH.exists():
            raise FileNotFoundError(
                f"ChromaDB directory not found: {CHROMA_PATH}"
            )

        embedding_function = OllamaEmbeddingFunction(
            model_name=EMBEDDING_MODEL,
            url=OLLAMA_EMBEDDING_URL,
        )

        client = chromadb.PersistentClient(
            path=str(CHROMA_PATH)
        )

        _collection = client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=embedding_function,
        )

        logger.info(
            "Connected to ChromaDB collection '%s' with %s records",
            COLLECTION_NAME,
            _collection.count(),
        )

    return _collection


# ============================================================
# 3. READ-ONLY SQLITE CONNECTION
# ============================================================

@contextmanager
def get_db_connection():
    """
    Open the SQLite database in read-only mode.
    The MCP tools cannot modify the database.
    """
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"SQLite database not found: {DB_PATH}"
        )

    connection = None

    try:
        database_uri = DB_PATH.as_uri() + "?mode=ro"

        connection = sqlite3.connect(
            database_uri,
            uri=True,
            timeout=5,
        )

        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only = ON")

        yield connection

    finally:
        if connection is not None:
            connection.close()


# ============================================================
# 4. DATABASE SCHEMA HELPERS
# ============================================================

def quote_identifier(identifier: str) -> str:
    """
    Safely quote a SQLite table or column identifier.
    """
    return '"' + identifier.replace('"', '""') + '"'


def get_books_columns(connection: sqlite3.Connection) -> list[str]:
    """
    Return the column names in the books table.
    """
    rows = connection.execute(
        f"PRAGMA table_info({quote_identifier('books')})"
    ).fetchall()

    if not rows:
        raise ValueError(
            "The 'books' table does not exist or has no columns."
        )

    return [row["name"] for row in rows]


def find_column(
    columns: list[str],
    aliases: list[str],
    required: bool = True,
) -> str | None:
    """
    Find a real database column using common column-name aliases.
    Matching is case-insensitive.
    """
    lookup = {
        column.casefold(): column
        for column in columns
    }

    for alias in aliases:
        if alias.casefold() in lookup:
            return lookup[alias.casefold()]

    if required:
        raise ValueError(
            f"Could not find a column matching any of: {aliases}. "
            f"Available columns: {columns}"
        )

    return None


# ============================================================
# 5. SAFE STATISTICS TOOL
# ============================================================

StatisticName = Literal[
    "total_books",
    "books_with_descriptions",
    "books_with_subjects",
    "top_authors",
    "publication_year_range",
]


@mcp.tool()
def get_book_statistics(
    statistic: StatisticName,
) -> dict[str, Any]:
    """
    Return one supported statistic about the local books database.

    Supported statistic values:
    - total_books: total number of books
    - books_with_descriptions: books with a non-empty description
    - books_with_subjects: books with non-empty subjects
    - top_authors: ten authors with the most book records
    - publication_year_range: earliest and latest valid publication years

    This tool runs only predefined queries. It does not accept SQL.
    """
    # Keep runtime validation even though the argument is typed.
    allowed_statistics = {
        "total_books",
        "books_with_descriptions",
        "books_with_subjects",
        "top_authors",
        "publication_year_range",
    }

    if statistic not in allowed_statistics:
        return {
            "success": False,
            "error": "Unsupported statistic.",
            "allowed_statistics": sorted(allowed_statistics),
        }

    try:
        with get_db_connection() as connection:
            columns = get_books_columns(connection)

            # -----------------------------------------------
            # STATISTIC 1: TOTAL BOOKS
            # -----------------------------------------------
            if statistic == "total_books":
                row = connection.execute(
                    "SELECT COUNT(*) AS total FROM books"
                ).fetchone()

                return {
                    "success": True,
                    "statistic": statistic,
                    "total_books": row["total"],
                }

            # -----------------------------------------------
            # STATISTIC 2: BOOKS WITH DESCRIPTIONS
            # -----------------------------------------------
            elif statistic == "books_with_descriptions":
                description_col = find_column(
                    columns,
                    ["description", "book-description", "summary"],
                )

                quoted_col = quote_identifier(description_col)

                row = connection.execute(
                    f"""
                    SELECT COUNT(*) AS total
                    FROM books
                    WHERE TRIM(COALESCE(CAST({quoted_col} AS TEXT), '')) != ''
                    """
                ).fetchone()

                return {
                    "success": True,
                    "statistic": statistic,
                    "books_with_descriptions": row["total"],
                }

            # -----------------------------------------------
            # STATISTIC 3: BOOKS WITH SUBJECTS
            # -----------------------------------------------
            elif statistic == "books_with_subjects":
                subjects_col = find_column(
                    columns,
                    ["subjects", "subject", "categories", "genres"],
                )

                quoted_col = quote_identifier(subjects_col)

                row = connection.execute(
                    f"""
                    SELECT COUNT(*) AS total
                    FROM books
                    WHERE TRIM(COALESCE(CAST({quoted_col} AS TEXT), '')) != ''
                    """
                ).fetchone()

                return {
                    "success": True,
                    "statistic": statistic,
                    "books_with_subjects": row["total"],
                }

            # -----------------------------------------------
            # STATISTIC 4: TOP AUTHORS
            # -----------------------------------------------
            elif statistic == "top_authors":
                author_col = find_column(
                    columns,
                    ["book-author", "author", "authors", "author_name"],
                )

                quoted_col = quote_identifier(author_col)

                rows = connection.execute(
                    f"""
                    SELECT
                        TRIM(CAST({quoted_col} AS TEXT)) AS author,
                        COUNT(*) AS book_count
                    FROM books
                    WHERE TRIM(
                        COALESCE(CAST({quoted_col} AS TEXT), '')
                    ) != ''
                    GROUP BY TRIM(CAST({quoted_col} AS TEXT))
                    ORDER BY book_count DESC, author ASC
                    LIMIT 10
                    """
                ).fetchall()

                return {
                    "success": True,
                    "statistic": statistic,
                    "top_authors": [
                        {
                            "author": row["author"],
                            "book_count": row["book_count"],
                        }
                        for row in rows
                    ],
                }

            # -----------------------------------------------
            # STATISTIC 5: PUBLICATION YEAR RANGE
            # -----------------------------------------------
            elif statistic == "publication_year_range":
                year_col = find_column(
                    columns,
                    [
                        "year-of-publication",
                        "publication_year",
                        "year",
                        "published_year",
                    ],
                )

                quoted_col = quote_identifier(year_col)

                # Accept only values consisting entirely of digits,
                # and restrict the range to plausible publication years.
                rows = connection.execute(
                    f"""
                    SELECT
                        MIN(CAST(TRIM(CAST({quoted_col} AS TEXT)) AS INTEGER))
                            AS earliest_year,
                        MAX(CAST(TRIM(CAST({quoted_col} AS TEXT)) AS INTEGER))
                            AS latest_year,
                        COUNT(*) AS valid_year_count
                    FROM books
                    WHERE TRIM(
                        COALESCE(CAST({quoted_col} AS TEXT), '')
                    ) != ''
                    AND TRIM(CAST({quoted_col} AS TEXT))
                        NOT GLOB '*[^0-9]*'
                    AND CAST(TRIM(CAST({quoted_col} AS TEXT)) AS INTEGER)
                        BETWEEN 1000 AND 2100
                    """
                ).fetchone()

                return {
                    "success": True,
                    "statistic": statistic,
                    "earliest_year": rows["earliest_year"],
                    "latest_year": rows["latest_year"],
                    "valid_year_count": rows["valid_year_count"],
                }

    except (sqlite3.Error, ValueError, FileNotFoundError) as exc:
        logger.exception(
            "Failed to calculate statistic: %s",
            statistic,
        )

        return {
            "success": False,
            "statistic": statistic,
            "error": str(exc),
        }


# ============================================================
# 6. SEMANTIC SEARCH TOOL
# ============================================================

@mcp.tool()
def semantic_search_books(
    query: str,
    top_k: Annotated[
        int,
        Field(
            ge=1,
            le=10,
            description="Number of matching books to return, from 1 to 10.",
        ),
    ] = 5,
) -> dict[str, Any]:
    """
    Search the local book collection using semantic similarity.

    Args:
        query: A natural-language question or description of the books
               you want to find.
        top_k: Number of results to return, from 1 to 10. Defaults to 5.

    Returns matching book text, metadata, and distance values.
    Lower distance generally indicates a closer match for the
    collection's configured distance metric. Distance is not a
    percentage or a guaranteed confidence score.
    """
    # Validate input at runtime as well.
    if not isinstance(query, str) or not query.strip():
        return {
            "success": False,
            "error": "The search query must be a non-empty string.",
        }

    if isinstance(top_k, bool) or not isinstance(top_k, int):
        return {
            "success": False,
            "error": "top_k must be an integer between 1 and 10.",
        }

    if not 1 <= top_k <= 10:
        return {
            "success": False,
            "error": "top_k must be between 1 and 10.",
        }

    try:
        collection = get_collection()

        total_records = collection.count()

        if total_records == 0:
            return {
                "success": True,
                "query": query,
                "results_count": 0,
                "results": [],
                "message": "The book collection is empty.",
            }

        # Do not ask ChromaDB for more records than it contains.
        result_limit = min(top_k, total_records)

        response = collection.query(
            query_texts=[query.strip()],
            n_results=result_limit,
            include=[
                "documents",
                "metadatas",
                "distances",
            ],
        )

        documents = response.get("documents") or [[]]
        metadatas = response.get("metadatas") or [[]]
        distances = response.get("distances") or [[]]

        documents = documents[0] if documents else []
        metadatas = metadatas[0] if metadatas else []
        distances = distances[0] if distances else []

        results = []

        for index, document in enumerate(documents):
            metadata = (
                metadatas[index]
                if index < len(metadatas) and metadatas[index]
                else {}
            )

            distance = (
                distances[index]
                if index < len(distances)
                else None
            )

            results.append(
                {
                    "rank": index + 1,
                    "document": document or "",
                    "metadata": metadata,
                    "distance": distance,
                }
            )

        return {
            "success": True,
            "query": query.strip(),
            "results_count": len(results),
            "results": results,
        }

    except Exception as exc:
        logger.exception("Semantic book search failed")

        return {
            "success": False,
            "query": query,
            "error": str(exc),
            "hint": (
                "Check that Ollama is running, the embedding model "
                "is available, and the ChromaDB collection exists."
            ),
        }


# ============================================================
# 7. START MCP SERVER
# ============================================================

if __name__ == "__main__":
    logger.info("Starting Ask My Data Books MCP server...")
    logger.info("SQLite database: %s", DB_PATH)
    logger.info("ChromaDB directory: %s", CHROMA_PATH)

    mcp.run(transport="stdio")

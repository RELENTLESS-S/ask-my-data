
from pathlib import Path

import chromadb
import pandas as pd
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction

# Project paths
PROJECT_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_DIR / "data" / "cleaned" / "books_with_metadata_filter.csv"
CHROMA_PATH = PROJECT_DIR / "chroma_db"

# Load the enriched book dataset
df = pd.read_csv(CSV_PATH, dtype={"isbn": str}).fillna("")

print(df.columns.tolist())

df = df.rename(columns={
    "book-title": "title",
    "book-author": "author",
    "isbn": "isbn",
    "description": "description",
    "subjects": "subjects",
})

# Connect to local, persistent ChromaDB
client = chromadb.PersistentClient(path=str(CHROMA_PATH))

# Use Ollama to generate embeddings
embedding_function = OllamaEmbeddingFunction(
    model_name="nomic-embed-text",
    url="http://localhost:11434/api/embeddings",
)

# Rebuild this collection whenever the indexing script runs
collection_name = "books_semantic"

try:
    client.delete_collection(collection_name)
except Exception:
    pass

collection = client.create_collection(
    name=collection_name,
    embedding_function=embedding_function,
    metadata={"hnsw:space": "cosine"},
)

# Convert book rows into searchable passages
ids = []
documents = []
metadatas = []

for row_number, row in df.iterrows():
    isbn = str(row["isbn"]).strip()

    # Skip rows without a usable ID
    if not isbn:
        continue

    title = str(row["title"]).strip()
    author = str(row["author"]).strip()
    description = str(row["description"]).strip()
    subjects = str(row["subjects"]).strip()

    passage = (
        f"Title: {title}\n"
        f"Author: {author}\n"
        f"Description: {description}\n"
        f"Subjects: {subjects}"
    )

    if not passage.strip():
        continue

    # Use a unique ID for each indexed passage
    chunk_id = f"book_{row_number}_{isbn}"

    ids.append(chunk_id)
    documents.append(passage)
    metadatas.append({
        "book_id": isbn,
        "chunk_index": 0,
        "title": title,
        "author": author,
    })

# Add data in batches
batch_size = 25

for start in range(0, len(documents), batch_size):
    end = start + batch_size

    collection.add(
        ids=ids[start:end],
        documents=documents[start:end],
        metadatas=metadatas[start:end],
    )

    print(f"Indexed {min(end, len(documents))}/{len(documents)} passages")

print("Indexing complete!")
print("Total indexed passages:", collection.count())
print("Database location:", CHROMA_PATH)

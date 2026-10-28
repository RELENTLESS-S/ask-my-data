from pathlib import Path
import chromadb

PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE_PATH = PROJECT_ROOT / "chroma_db_backup"

COLLECTION_NAME = "books_semantic"
BATCH_SIZE = 100

# Read from the backup, leaving the live index untouched.
if not SOURCE_PATH.exists():
    raise FileNotFoundError(f"Backup not found: {SOURCE_PATH}")

source_client = chromadb.PersistentClient(path=str(SOURCE_PATH))
source = source_client.get_collection(COLLECTION_NAME)

source_count = source.count()
print(f"Source documents: {source_count}")

if source_count != 732:
    raise RuntimeError(
        f"Expected 732 source documents, found {source_count}. "
        "Stopping without migrating."
    )

# Connect to the Docker ChromaDB service through the
# temporary localhost-only port mapping.
target_client = chromadb.HttpClient(
    host="localhost",
    port=8001
)

# Never overwrite an existing destination collection.
existing = [
    c.name for c in target_client.list_collections()
]

if COLLECTION_NAME in existing:
    target = target_client.get_collection(COLLECTION_NAME)
    raise RuntimeError(
        f"Destination collection already exists with "
        f"{target.count()} documents. No changes made. "
        "Stop and inspect before continuing."
    )

target = target_client.create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"}
)

# Copy stored vectors directly; do not re-embed the documents.
for offset in range(0, source_count, BATCH_SIZE):
    batch = source.get(
        limit=BATCH_SIZE,
        offset=offset,
        include=["documents", "metadatas", "embeddings"]
    )

    embeddings = batch["embeddings"]
    if hasattr(embeddings, "tolist"):
        embeddings = embeddings.tolist()

    if not embeddings or len(embeddings) != len(batch["ids"]):
        raise RuntimeError(
            f"Missing or incomplete embeddings at offset {offset}"
        )

    target.add(
        ids=batch["ids"],
        documents=batch["documents"],
        metadatas=batch["metadatas"],
        embeddings=embeddings
    )

    print(
        f"Migrated {min(offset + len(batch['ids']), source_count)}"
        f" / {source_count}"
    )

# Verify the completed transfer.
target_count = target.count()
print(f"\nDestination documents: {target_count}")

if target_count != source_count:
    raise RuntimeError("Count mismatch! Do not proceed.")

sample = target.get(
    limit=1,
    include=["documents", "metadatas", "embeddings"]
)
print("Sample ID:", sample["ids"][0])
print("Sample metadata:", sample["metadatas"][0])
print("Embedding dimensions:", len(sample["embeddings"][0]))
print("Migration completed and verified.")


from pathlib import Path
import chromadb
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction

# Project root: ask-my-data
PROJECT_DIR = Path(__file__).resolve().parent.parent
VECTOR_PATH = PROJECT_DIR / "chroma_db"

# Connect to the existing vector database
client = chromadb.PersistentClient(path=str(VECTOR_PATH))

# Use the same embedding model as indexing
embedding_function = OllamaEmbeddingFunction(
    model_name="nomic-embed-text",
    url="http://localhost:11434/api/embeddings",
)

# Access the existing collection
collection = client.get_collection(
    name="books_semantic",
    embedding_function=embedding_function,
)

def search_books(question, top_k=3):
    # results = collection.query(
    #     query_texts=[question],
    #     n_results=top_k,
    # )
    
    results = collection.query(
    query_texts=[question],
    n_results=top_k,
    include=["documents", "metadatas", "distances"]
    )

    print("\nDOCUMENTS:")
    print(results["documents"])

    print("\nMETADATA:")
    print(results["metadatas"])

    print("\nDISTANCES:")
    print(results["distances"])

    for i, document in enumerate(results["documents"][0]):
        distance = results["distances"][0][i]
        metadata = results["metadatas"][0][i]

        print(f"\nResult {i + 1}")
        print(f"Similarity distance: {distance:.4f}")
        print(f"Book details: {metadata}")
        print(f"Text: {document}")

if __name__ == "__main__":
    question = input("Ask a question about the books: ")
    search_books(question)

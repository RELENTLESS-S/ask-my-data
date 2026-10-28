
from pathlib import Path

import chromadb
import ollama
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction

# 1. Find the project root
PROJECT_DIR = Path(__file__).resolve().parent.parent
VECTOR_PATH = PROJECT_DIR / "chroma_db"

# 2. Connect to the existing vector database
client = chromadb.PersistentClient(path=str(VECTOR_PATH))

# 3. Use the same embedding model used during indexing
embedding_function = OllamaEmbeddingFunction(
    model_name="nomic-embed-text",
    url="http://localhost:11434/api/embeddings",
)

# 4. Access the existing collection
collection = client.get_collection(
    name="books_semantic",
    embedding_function=embedding_function,
)

CHAT_MODEL = "gemma4:e2b"


def ask_books(question, top_k=10):
    # Step A: Retrieve relevant books
    results = collection.query(
        query_texts=[question],
        n_results=top_k,
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]

    if not documents:
        print("No relevant books were found.")
        return

    # Step B: Build context from retrieved books
    context_parts = []

    for i, document in enumerate(documents):
        metadata = metadatas[i] or {}

        title = metadata.get("title", "Unknown title")
        author = metadata.get("author", "Unknown author")
        description = metadata.get("description", "")
        subjects = metadata.get("subjects", "")

        context_parts.append(
            f"Book {i + 1}:\n"
            f"Title: {title}\n"
            f"Author: {author}\n"
            f"Description: {description}\n"
            f"Subjects: {subjects}\n"
            f"Retrieved document: {document}"
        )

    context = "\n\n".join(context_parts)

    # Step C: Ask the chat model to answer from the context
    response = ollama.chat(
        model=CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant for a book database. "
                    "Answer using only the supplied book context. "
                    "If the context does not contain the answer, "
                    "say that the available book data is insufficient. "
                    "Do not invent book details."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n\n"
                    f"Retrieved book context:\n{context}"
                ),
            },
        ],
    )

    # Step D: Display the answer
    print("\nANSWER")
    print(response.message.content)

    # Step E: Display sources
    print("\nRETRIEVED SOURCES")

    for i, metadata in enumerate(metadatas):
        metadata = metadata or {}
        print(
            f"{i + 1}. "
            f"{metadata.get('title', 'Unknown title')} "
            f"— {metadata.get('author', 'Unknown author')}"
        )


if __name__ == "__main__":
    question = input("Ask a question about your books: ").strip()

    if question:
        ask_books(question)

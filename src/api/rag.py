
# src/api/rag.py

import logging
import os
from pathlib import Path

import chromadb
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHROMA_PATH = PROJECT_ROOT / "chroma_db"
PROMPT_PATH = PROJECT_ROOT / "prompts" / "answer.txt"

COLLECTION_NAME = "books_semantic"

CHROMA_HOST = os.getenv("CHROMA_HOST")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434"
).rstrip("/")

OLLAMA_MODEL = os.getenv("CHAT_MODEL", "llama3.2:1b")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

# Connect to remote ChromaDB in Docker or local ChromaDB otherwise.
if CHROMA_HOST:
    client = chromadb.HttpClient(
        host=CHROMA_HOST,
        port=CHROMA_PORT
    )
else:
    client = chromadb.PersistentClient(
        path=str(CHROMA_PATH)
    )

# Do not attach a new embedding function to this existing collection.
# We generate query embeddings explicitly using Ollama instead.
collection = client.get_collection(name=COLLECTION_NAME)


def create_query_embedding(question: str) -> list[float]:
    """Generate a question embedding using the configured Ollama model."""

    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/embeddings",
        json={
            "model": EMBEDDING_MODEL,
            "prompt": question
        },
        timeout=120
    )
    response.raise_for_status()

    embedding = response.json().get("embedding")

    if not embedding:
        raise ValueError("Ollama returned an empty question embedding.")

    return embedding


def answer_question(question: str, top_k: int = 5) -> dict:
    try:
        if not question or not question.strip():
            return {
                "answer": "Please provide a valid question.",
                "sources": []
            }

        # Embed the question using the same model used for the book index.
        query_embedding = create_query_embedding(question)

        # Search existing vectors without modifying the collection.
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas"]
        )

        documents = results["documents"][0] or []
        metadatas = results["metadatas"][0] or []

        if not documents:
            return {
                "answer": (
                    "I don't have enough information in the retrieved "
                    "book data to answer that question."
                ),
                "sources": []
            }

        context_parts = []

        for i, document in enumerate(documents, start=1):
            context_parts.append(f"[Source {i}]\n{document}")

        context = "\n\n".join(context_parts)

        if not PROMPT_PATH.exists():
            raise FileNotFoundError(
                f"Prompt file not found: {PROMPT_PATH}"
            )

        template = PROMPT_PATH.read_text(encoding="utf-8")
        prompt = template.format(
            context=context,
            question=question
        )

        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            },
            timeout=120
        )
        response.raise_for_status()

        answer = response.json()["message"]["content"]

        sources = [
            {
                "text": document,
                "metadata": metadata or {}
            }
            for document, metadata in zip(documents, metadatas)
        ]

        return {
            "answer": answer,
            "sources": sources
        }

    except Exception:
        logging.exception("Error inside answer_question()")
        raise

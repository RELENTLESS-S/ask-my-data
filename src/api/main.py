# src/api/main.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from api.rag import answer_question
from api.database import get_stats

app = FastAPI(
    title="Ask My Data API",
    description="Ask questions about a book collection using RAG.",
    version="1.0.0"
)


class AskRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=2000,
        description="Question about the book collection"
    )
    top_k: int = Field(default=5, ge=1, le=10)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "Ask My Data API"
    }


@app.get("/stats")
def stats():
    try:
        return get_stats()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve database statistics."
        ) from exc


@app.post("/ask")
def ask(request: AskRequest):
    try:
        return answer_question(
            question=request.question,
            top_k=request.top_k
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to answer the question."
        ) from exc

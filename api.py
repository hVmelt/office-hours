"""
FastAPI backend for the office-hours RAG system.

Endpoints:
  GET  /                  -> health check
  GET  /documents         -> list indexed documents
  POST /documents         -> upload + index a new PDF
  POST /ask               -> answer a question with citations
"""

from pathlib import Path
import tempfile

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, UploadFile, HTTPException
from pydantic import BaseModel

from chunker import chunk_pdf
from embedder import embed_texts
from retriever import top_k
from prompt import answer as build_answer
from db import get_connection
from ingest import is_indexed


app = FastAPI(
    title="Office Hours",
    description="RAG-powered Q&A over course material with cited sources.",
    version="0.1.0",
)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Request / response models ----------
# Pydantic models give us automatic validation and auto-generated API docs.

class AskRequest(BaseModel):
    question: str
    k: int = 5


class Citation(BaseModel):
    doc: str
    page: int
    score: float


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]


class Document(BaseModel):
    id: int
    name: str
    filename: str
    num_pages: int
    indexed_at: str


# ---------- Endpoints ----------

@app.get("/")
def health():
    """Health check."""
    return {"status": "ok", "service": "office-hours"}


@app.get("/documents", response_model=list[Document])
def list_documents():
    """Return all indexed documents."""
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, name, filename, num_pages, indexed_at FROM documents ORDER BY indexed_at DESC"
        )
        rows = cur.fetchall()
    return [
        Document(
            id=row[0],
            name=row[1],
            filename=row[2],
            num_pages=row[3],
            indexed_at=row[4].isoformat(),
        )
        for row in rows
    ]


@app.post("/documents", response_model=Document)
async def upload_document(file: UploadFile):
    """Upload a PDF and index it into the database."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    doc_name = Path(file.filename).stem
    conn = get_connection()
    try:
        if is_indexed(conn, doc_name):
            raise HTTPException(
                status_code=409,
                detail=f"Document '{doc_name}' is already indexed.",
            )

        # Save the uploaded file to a temp location so chunker can read it.
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            chunks = chunk_pdf(tmp_path)
            num_pages = max(c["page"] for c in chunks)
            vectors = embed_texts([c["text"] for c in chunks], input_type="document")

            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO documents (name, filename, num_pages)
                    VALUES (%s, %s, %s)
                    RETURNING id, indexed_at
                    """,
                    (doc_name, file.filename, num_pages),
                )
                document_id, indexed_at = cur.fetchone()

                cur.executemany(
                    """
                    INSERT INTO chunks (document_id, page, chunk_index, text, embedding)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    [
                        (document_id, chunk["page"], i, chunk["text"], vector)
                        for i, (chunk, vector) in enumerate(zip(chunks, vectors))
                    ],
                )
            conn.commit()
        finally:
            tmp_path.unlink(missing_ok=True)

        return Document(
            id=document_id,
            name=doc_name,
            filename=file.filename,
            num_pages=num_pages,
            indexed_at=indexed_at.isoformat(),
        )
    finally:
        conn.close()


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    """Answer a question with citations to source pages."""
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    query_vec = embed_texts([req.question], input_type="query")[0]
    retrieved = top_k(query_vec, k=req.k)

    if not retrieved:
        raise HTTPException(
            status_code=503,
            detail="No documents are indexed yet. Upload a PDF first.",
        )

    answer_text = build_answer(req.question, retrieved)

    return AskResponse(
        answer=answer_text,
        citations=[
            Citation(doc=c["doc"], page=c["page"], score=c["score"])
            for c in retrieved
        ],
    )
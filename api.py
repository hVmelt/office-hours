"""
FastAPI backend for the office-hours RAG system.

Endpoints:
  GET  /                  -> health check
  GET  /documents         -> list documents visible to this session (demo + own)
  POST /documents         -> upload + index a new PDF (tagged with session)
  POST /ask               -> answer a question with citations
  DELETE /documents/{id}  -> delete a document owned by this session
"""

from pathlib import Path
import tempfile

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, UploadFile, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from chunker import chunk_pdf
from embedder import embed_texts
from retriever import top_k
from prompt import answer as build_answer
from db import get_connection


app = FastAPI(
    title="Office Hours",
    description="RAG-powered Q&A over course material with cited sources.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://office-hours-two.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Request / response models ----------

class AskRequest(BaseModel):
    question: str
    k: int = 5


class Citation(BaseModel):
    doc: str
    page: int
    score: float
    text: str


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]


class Document(BaseModel):
    id: int
    name: str
    filename: str
    num_pages: int
    indexed_at: str
    is_demo: bool


# ---------- Helpers ----------

def doc_exists_for_session(conn, doc_name: str, session_id: str | None) -> bool:
    """
    Check if a document with this name already exists for this session
    (or as a demo doc). Prevents duplicate uploads within a session
    without blocking different sessions from using the same filename.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM documents
            WHERE name = %s AND (is_demo = TRUE OR session_id = %s)
            """,
            (doc_name, session_id),
        )
        return cur.fetchone() is not None


# ---------- Endpoints ----------

@app.get("/")
def health():
    """Health check."""
    return {"status": "ok", "service": "office-hours"}


@app.get("/documents", response_model=list[Document])
def list_documents(x_session_id: str | None = Header(default=None)):
    """Return demo documents plus any owned by this session."""
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, filename, num_pages, indexed_at, is_demo
            FROM documents
            WHERE is_demo = TRUE OR session_id = %s
            ORDER BY is_demo DESC, indexed_at DESC
            """,
            (x_session_id,),
        )
        rows = cur.fetchall()
    return [
        Document(
            id=row[0],
            name=row[1],
            filename=row[2],
            num_pages=row[3],
            indexed_at=row[4].isoformat(),
            is_demo=row[5],
        )
        for row in rows
    ]


@app.post("/documents", response_model=Document)
async def upload_document(
    file: UploadFile,
    x_session_id: str | None = Header(default=None),
):
    """Upload a PDF and index it, tagged to this session."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    if x_session_id is None:
        raise HTTPException(status_code=400, detail="Missing session identifier.")

    doc_name = Path(file.filename).stem
    conn = get_connection()
    try:
        if doc_exists_for_session(conn, doc_name, x_session_id):
            raise HTTPException(
                status_code=409,
                detail=f"You've already uploaded a document named '{doc_name}'.",
            )

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
                    INSERT INTO documents (name, filename, num_pages, session_id, is_demo)
                    VALUES (%s, %s, %s, %s, FALSE)
                    RETURNING id, indexed_at
                    """,
                    (doc_name, file.filename, num_pages, x_session_id),
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
            is_demo=False,
        )
    finally:
        conn.close()


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest, x_session_id: str | None = Header(default=None)):
    """Answer a question using demo docs + this session's docs."""
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    query_vec = embed_texts([req.question], input_type="query")[0]
    retrieved = top_k(query_vec, k=req.k, session_id=x_session_id)

    if not retrieved:
        raise HTTPException(
            status_code=503,
            detail="No documents available. Upload a PDF first.",
        )

    answer_text = build_answer(req.question, retrieved)

    return AskResponse(
        answer=answer_text,
        citations=[
            Citation(doc=c["doc"], page=c["page"], score=c["score"], text=c["text"])
            for c in retrieved
        ],
    )


@app.delete("/documents/{document_id}")
def delete_document(
    document_id: int,
    x_session_id: str | None = Header(default=None),
):
    """Delete a document, but only if it's owned by this session (not a demo doc)."""
    with get_connection() as conn, conn.cursor() as cur:
        # Only delete if it belongs to this session AND isn't a demo doc.
        cur.execute(
            """
            DELETE FROM documents
            WHERE id = %s AND session_id = %s AND is_demo = FALSE
            RETURNING id
            """,
            (document_id, x_session_id),
        )
        result = cur.fetchone()
        if result is None:
            raise HTTPException(
                status_code=404,
                detail="Document not found, or you don't have permission to delete it.",
            )
        conn.commit()
    return {"deleted": document_id}
"""
Index PDFs from docs/ into Postgres.
Skips documents that are already indexed.
"""

from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from chunker import chunk_pdf, load_pdf_pages
from embedder import embed_texts
from db import get_connection


def is_indexed(conn, doc_name: str) -> bool:
    """Check if a document is already in the database."""
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM documents WHERE name = %s", (doc_name,))
        return cur.fetchone() is not None


def ingest_pdf(conn, pdf_path: Path) -> None:
    doc_name = pdf_path.stem

    if is_indexed(conn, doc_name):
        print(f"  {doc_name}: already indexed, skipping")
        return

    print(f"  {doc_name}: chunking...")
    chunks = chunk_pdf(pdf_path)
    num_pages = max(c["page"] for c in chunks)
    print(f"    {len(chunks)} chunks across {num_pages} pages")

    print(f"  {doc_name}: embedding...")
    vectors = embed_texts([c["text"] for c in chunks], input_type="document")

    print(f"  {doc_name}: inserting into Postgres...")
    with conn.cursor() as cur:
        # Insert the document row, get its auto-generated ID back.
        cur.execute(
            """
            INSERT INTO documents (name, filename, num_pages)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (doc_name, pdf_path.name, num_pages),
        )
        document_id = cur.fetchone()[0]

        # Batch-insert all chunks for this document.
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

    # Commit the transaction. Without this, nothing actually saves.
    conn.commit()
    print(f"  {doc_name}: done ({len(chunks)} chunks indexed)\n")


def main():
    docs_dir = Path("docs")
    print(f"Indexing PDFs from {docs_dir}/\n")

    conn = get_connection()
    try:
        for pdf_path in sorted(docs_dir.glob("*.pdf")):
            ingest_pdf(conn, pdf_path)
    finally:
        conn.close()

    print("Done.")


if __name__ == "__main__":
    main()
"""
Smarter chunking: respect paragraph boundaries, add overlap between chunks.
Each chunk knows which document and page it came from.
"""

from pathlib import Path
from pypdf import PdfReader


def load_pdf_pages(pdf_path: Path) -> list[dict]:
    """Return [{page, text}] for every page that has text."""
    reader = PdfReader(str(pdf_path))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append({"page": i, "text": text})
    return pages


def chunk_text(
    text: str,
    target_words: int = 250,
    overlap_words: int = 50,
) -> list[str]:
    """
    Split text into chunks of ~target_words, respecting paragraph breaks.
    Each chunk overlaps the previous one by overlap_words so we don't lose
    context at chunk boundaries.

    Strategy: split into paragraphs, then greedily pack paragraphs into
    chunks until we hit target_words. When we start a new chunk, include
    the last overlap_words of the previous chunk as a prefix.
    """
    # Split on blank lines (paragraph breaks). pypdf often gives us
    # single newlines per visual line, so we split on double newlines.
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks: list[str] = []
    current_words: list[str] = []

    for para in paragraphs:
        para_words = para.split()
        # If adding this paragraph would overflow, finalize current chunk.
        if current_words and len(current_words) + len(para_words) > target_words:
            chunks.append(" ".join(current_words))
            # Start next chunk with overlap from the previous one.
            current_words = current_words[-overlap_words:] if overlap_words > 0 else []
        current_words.extend(para_words)

    if current_words:
        chunks.append(" ".join(current_words))

    return chunks


def chunk_pdf(pdf_path: Path) -> list[dict]:
    """
    Returns [{doc, page, text}] for every chunk in the PDF.
    We chunk per-page so we can cite the page number on every chunk.
    """
    doc_name = pdf_path.stem  # filename without extension
    pages = load_pdf_pages(pdf_path)

    all_chunks = []
    for page in pages:
        for chunk_text_str in chunk_text(page["text"]):
            all_chunks.append({
                "doc": doc_name,
                "page": page["page"],
                "text": chunk_text_str,
            })
    return all_chunks


def chunk_all_pdfs(docs_dir: Path) -> list[dict]:
    """Chunk every PDF in the docs/ folder. Returns a flat list of chunks."""
    all_chunks = []
    for pdf_path in sorted(docs_dir.glob("*.pdf")):
        print(f"  chunking {pdf_path.name}...")
        chunks = chunk_pdf(pdf_path)
        all_chunks.extend(chunks)
        print(f"    {len(chunks)} chunks")
    return all_chunks
"""
Smarter chunking: respect paragraph boundaries, add overlap between chunks.
Each chunk knows which document and page it came from.
"""

from pathlib import Path
from pypdf import PdfReader
from collections import Counter


def _find_repeated_lines(pages_text: list[str], min_pages_threshold: float = 0.5) -> set[str]:
    """
    Find lines that appear on a significant fraction of pages.
    These are almost always headers, footers, page numbers, or running titles.

    A line is "repeated" if it shows up on at least min_pages_threshold (default 50%)
    of pages with text.
    """
    line_counts: Counter[str] = Counter()
    for page_text in pages_text:
        # dedupe within a page first — we want lines that repeat ACROSS pages,
        # not lines that happen to be duplicated within one page
        unique_lines = {line.strip() for line in page_text.split("\n") if line.strip()}
        for line in unique_lines:
            line_counts[line] += 1

    threshold = max(2, int(len(pages_text) * min_pages_threshold))
    return {line for line, count in line_counts.items() if count >= threshold}


def _clean_page_text(text: str, junk_lines: set[str]) -> str:
    """Remove header/footer lines from a page. Preserve paragraph structure."""
    kept_lines = []
    for line in text.split("\n"):
        if line.strip() in junk_lines:
            continue
        kept_lines.append(line)
    return "\n".join(kept_lines).strip()


def load_pdf_pages(pdf_path: Path) -> list[dict]:
    """
    Return [{page, text}] for every page that has text,
    with repeated headers/footers stripped out.
    """
    reader = PdfReader(str(pdf_path))
    raw_pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            raw_pages.append({"page": i, "text": text})

    # Detect lines that appear on many pages — these are headers/footers.
    junk_lines = _find_repeated_lines([p["text"] for p in raw_pages])

    # Strip those lines from each page.
    cleaned = []
    for page in raw_pages:
        clean_text = _clean_page_text(page["text"], junk_lines)
        if clean_text:  # only keep pages that still have content
            cleaned.append({"page": page["page"], "text": clean_text})

    return cleaned


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
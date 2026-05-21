import os
from pathlib import Path
import numpy as np
from dotenv import load_dotenv
from pypdf import PdfReader
import voyageai
from anthropic import Anthropic

load_dotenv()

# Initialize clients. The libraries auto-read the keys from env vars.
voyage = voyageai.Client()
claude = Anthropic()


# ---------- 1. Load the PDF and extract text per page ----------
def load_pdf(path: str) -> list[dict]:
    """Return a list of {page_num, text} dicts, one per page."""
    reader = PdfReader(path)
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append({"page": i, "text": text})
    return pages


# ---------- 2. Chunk the text ----------
def chunk_pages(pages: list[dict], target_size: int = 500) -> list[dict]:
    """
    Split each page into chunks of ~target_size words.
    Keep the page number on each chunk so we can cite it later.
    For day 1 we use a dead-simple word-count split.
    """
    chunks = []
    for page in pages:
        words = page["text"].split()
        for start in range(0, len(words), target_size):
            chunk_words = words[start : start + target_size]
            chunks.append({
                "page": page["page"],
                "text": " ".join(chunk_words),
            })
    return chunks


# ---------- 3. Embed everything ----------
def embed_texts(texts: list[str], input_type: str) -> np.ndarray:
    """
    Call Voyage to embed a list of strings.
    input_type is 'document' for stored chunks, 'query' for questions.
    Voyage uses different internal processing for each — this matters.
    Returns a NumPy array of shape (n_texts, embedding_dim).
    """
    result = voyage.embed(texts, model="voyage-3", input_type=input_type)
    return np.array(result.embeddings)


# ---------- 4. Find the closest chunks to a query ----------
def top_k_chunks(query_vec: np.ndarray, chunk_vecs: np.ndarray, k: int = 5) -> list[int]:
    """
    Cosine similarity = dot product of unit vectors.
    Voyage embeddings are already L2-normalized, so dot product is enough.
    Return the indices of the top-k most similar chunks.
    """
    similarities = chunk_vecs @ query_vec  # shape: (n_chunks,)
    top_indices = np.argsort(similarities)[::-1][:k]
    return top_indices.tolist()


# ---------- 5. Ask Claude using the retrieved chunks ----------
def answer(question: str, retrieved: list[dict]) -> str:
    """Build a RAG prompt and call Claude."""
    context = "\n\n".join(
        f"[Source: page {c['page']}]\n{c['text']}"
        for c in retrieved
    )

    prompt = f"""You are answering a student's question using only the provided excerpts from their course material.

Excerpts:
{context}

Student question: {question}

Instructions:
- Answer using only the information in the excerpts.
- Cite the page number for each claim, like (page 4).
- If the excerpts don't contain the answer, say so honestly."""

    response = claude.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


# ---------- Tie it all together ----------
def main():
    print("Loading PDF...")
    pages = load_pdf("doc.pdf")
    print(f"  {len(pages)} pages with text")

    print("Chunking...")
    chunks = chunk_pages(pages)
    print(f"  {len(chunks)} chunks")

    print("Embedding chunks (this may take a few seconds)...")
    chunk_vecs = embed_texts([c["text"] for c in chunks], input_type="document")
    print(f"  vectors shape: {chunk_vecs.shape}")

    # Ask a question. Edit this to fit whatever's actually in your PDF.
    question = "What is the difference between Sunni and Shia Muslims, and how did the split happen?"

    print(f"\nQuestion: {question}\n")
    print("Embedding question...")
    query_vec = embed_texts([question], input_type="query")[0]

    print("Retrieving top 5 chunks...")
    top_indices = top_k_chunks(query_vec, chunk_vecs, k=5)
    retrieved = [chunks[i] for i in top_indices]
    print(f"  retrieved pages: {[c['page'] for c in retrieved]}")

    print("\nAsking Claude...\n")
    print("-" * 60)
    print(answer(question, retrieved))
    print("-" * 60)


if __name__ == "__main__":
    main()
"""
Day 2 driver: chunk all PDFs in docs/, embed with caching, answer a question.
"""

from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from chunker import chunk_all_pdfs
from embedder import embed_texts
from retriever import top_k
from prompt import answer


def main():
    docs_dir = Path("docs")

    print("Chunking PDFs...")
    chunks = chunk_all_pdfs(docs_dir)
    print(f"Total: {len(chunks)} chunks across all docs\n")

    print("Embedding chunks...")
    chunk_vecs = embed_texts([c["text"] for c in chunks], input_type="document")
    print(f"  shape: {chunk_vecs.shape}\n")

    # Try whatever question you want.
    question = "What happened at the Battle of Tours?"
    print(f"Question: {question}\n")
    print("Embedding question...")
    query_vec = embed_texts([question], input_type="query")[0]

    print("Retrieving top 5 chunks...")
    retrieved = top_k(query_vec, chunk_vecs, chunks, k=5)
    print("  retrieved:")
    for c in retrieved:
        print(f"    {c['doc']} page {c['page']} (score {c['score']:.3f})")

    print("\nAsking Claude...\n")
    print("-" * 60)
    print(answer(question, retrieved))
    print("-" * 60)


if __name__ == "__main__":
    main()
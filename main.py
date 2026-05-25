"""
Day 3 driver: query the Postgres-backed RAG system.
Note: this no longer does indexing — run `python ingest.py` separately for that.
"""

from dotenv import load_dotenv

load_dotenv()

from embedder import embed_texts
from retriever import top_k
from prompt import answer


def main():
    question = "What is the difference between Sunni and Shia Muslims?"

    print(f"Question: {question}\n")

    print("Embedding question...")
    query_vec = embed_texts([question], input_type="query")[0]

    print("Retrieving top 5 chunks...")
    retrieved = top_k(query_vec, k=5)
    print("  retrieved:")
    for c in retrieved:
        print(f"    {c['doc']} page {c['page']} (score {c['score']:.3f})")

    print("\nAsking Claude...\n")
    print("-" * 60)
    print(answer(question, retrieved))
    print("-" * 60)


if __name__ == "__main__":
    main()
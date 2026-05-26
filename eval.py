"""
Evaluate retrieval quality against a hand-curated set of questions.

Metrics:
- top-1 doc accuracy: was the highest-ranked chunk from the right doc?
- top-5 doc accuracy: was any of the top-5 chunks from the right doc?
- top-5 page recall: did we retrieve at least one of the expected pages?
- mean reciprocal rank (MRR): how high was the first correct chunk ranked?
"""

import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from embedder import embed_texts
from retriever import top_k


def evaluate_one(case: dict, k: int = 5) -> dict:
    """Run retrieval for one question and score the result."""
    question = case["question"]
    expected_doc = case["expected_doc"]
    expected_pages = set(case["expected_pages"])

    query_vec = embed_texts([question], input_type="query")[0]
    retrieved = top_k(query_vec, k=k)

    # Top-1: was the first chunk from the right doc on a right page?
    top1_doc_correct = retrieved[0]["doc"] == expected_doc
    top1_page_correct = (
        retrieved[0]["doc"] == expected_doc
        and retrieved[0]["page"] in expected_pages
    )

    # Top-k: did the right answer appear anywhere in the top k?
    topk_doc_correct = any(c["doc"] == expected_doc for c in retrieved)
    topk_page_correct = any(
        c["doc"] == expected_doc and c["page"] in expected_pages
        for c in retrieved
    )

    # Mean Reciprocal Rank: 1/rank of the first correct chunk, or 0 if none found.
    # MRR=1 means perfect, MRR=0.5 means the right chunk was 2nd, etc.
    rr = 0.0
    for i, chunk in enumerate(retrieved, start=1):
        if chunk["doc"] == expected_doc and chunk["page"] in expected_pages:
            rr = 1.0 / i
            break

    return {
        "question": question,
        "expected": f"{expected_doc} page(s) {sorted(expected_pages)}",
        "got_top1": f"{retrieved[0]['doc']} p{retrieved[0]['page']}",
        "top1_doc_correct": top1_doc_correct,
        "top1_page_correct": top1_page_correct,
        "topk_doc_correct": topk_doc_correct,
        "topk_page_correct": topk_page_correct,
        "reciprocal_rank": rr,
    }


def main():
    eval_set = json.loads(Path("eval_set.json").read_text())
    print(f"Running eval on {len(eval_set)} questions...\n")

    results = [evaluate_one(case) for case in eval_set]

    # Per-question breakdown
    print(f"{'Q':<60} {'expected':<22} {'got':<14} {'RR':>5}")
    print("-" * 105)
    for r in results:
        marker = "✓" if r["top1_page_correct"] else ("~" if r["topk_page_correct"] else "✗")
        q = r["question"][:55] + "..." if len(r["question"]) > 58 else r["question"]
        print(f"{marker} {q:<58} {r['expected']:<22} {r['got_top1']:<14} {r['reciprocal_rank']:>5.2f}")

    # Aggregate metrics
    n = len(results)
    top1_doc = sum(r["top1_doc_correct"] for r in results) / n
    top1_page = sum(r["top1_page_correct"] for r in results) / n
    topk_doc = sum(r["topk_doc_correct"] for r in results) / n
    topk_page = sum(r["topk_page_correct"] for r in results) / n
    mrr = sum(r["reciprocal_rank"] for r in results) / n

    print("\n" + "=" * 60)
    print(f"Top-1 doc accuracy:   {top1_doc:.1%}  ({int(top1_doc*n)}/{n})")
    print(f"Top-1 page accuracy:  {top1_page:.1%}  ({int(top1_page*n)}/{n})")
    print(f"Top-5 doc accuracy:   {topk_doc:.1%}  ({int(topk_doc*n)}/{n})")
    print(f"Top-5 page accuracy:  {topk_page:.1%}  ({int(topk_page*n)}/{n})")
    print(f"Mean Reciprocal Rank: {mrr:.3f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
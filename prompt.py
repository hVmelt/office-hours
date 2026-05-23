"""
Build the RAG prompt and call Claude.
Keeping this separate makes it easy to iterate on prompt design.
"""

from anthropic import Anthropic

claude = Anthropic()
MODEL = "claude-sonnet-4-5"


def build_prompt(question: str, retrieved: list[dict]) -> str:
    """Format retrieved chunks into a citation-friendly context block."""
    context = "\n\n".join(
        f"[Source: {c['doc']}, page {c['page']}]\n{c['text']}"
        for c in retrieved
    )

    return f"""You are answering a student's question using only the provided excerpts from their course material.

Excerpts:
{context}

Student question: {question}

Instructions:
- Answer using only the information in the excerpts.
- Cite the source for each claim, like (islam, page 4) or (charlemagne, page 2).
- If the excerpts don't contain the answer, say so honestly — do not fall back on general knowledge."""


def answer(question: str, retrieved: list[dict]) -> str:
    response = claude.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": build_prompt(question, retrieved)}],
    )
    return response.content[0].text
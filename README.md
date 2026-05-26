# office-hours

An AI study assistant that answers questions about course material with citations to the source page. Powered by retrieval-augmented generation (RAG).

## Stack

- **LLM:** Anthropic Claude (Sonnet 4.5)
- **Embeddings:** Voyage AI (voyage-3)
- **PDF parsing:** pypdf
- **Vector math:** NumPy (in-memory for now; pgvector coming on day 3)

## Running it locally

1. `pip install -r requirements.txt`
2. Add API keys to `.env` (see `.env.example`)
3. Put a PDF in the project root as `doc.pdf`
4. `python day1.py`

## Running the API

```bash
docker compose up -d                                         # start Postgres
python ingest.py                                             # index any PDFs in docs/
uvicorn api:app --reload                                     # start the API on port 8000
```

Then open http://localhost:8000/docs for interactive API documentation.

### Endpoints

- `GET /` — health check
- `GET /documents` — list indexed documents
- `POST /documents` — upload and index a PDF
- `POST /ask` — answer a question with cited sources

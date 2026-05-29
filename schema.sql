-- Enable pgvector (idempotent - safe to run multiple times)
CREATE EXTENSION IF NOT EXISTS vector;
-- One row per indexed PDF
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    filename TEXT NOT NULL,
    num_pages INTEGER NOT NULL,
    session_id TEXT,
    is_demo BOOLEAN NOT NULL DEFAULT FALSE,
    indexed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS documents_session_idx ON documents(session_id);
-- One row per chunk; holds the embedding
CREATE TABLE IF NOT EXISTS chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    embedding vector(1024) NOT NULL
);
-- Indexes
CREATE INDEX IF NOT EXISTS chunks_embedding_idx ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS chunks_document_id_idx ON chunks(document_id);
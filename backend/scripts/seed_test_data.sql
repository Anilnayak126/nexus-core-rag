-- Dev/CI test-data seed
-- Schema is auto-created by the application on first start.
-- This layers demo data for development / CI testing.
-- Idempotent: safe to run multiple times.

-- Ensure required extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Ensure tables exist (safe to run even after app init)
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT,
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id),
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(384),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chunk_embedding
ON document_chunks
USING hnsw (embedding vector_cosine_ops);

-- Ensure unique constraints for idempotent inserts
-- Clean up any duplicate seed data from previous runs
DELETE FROM document_chunks WHERE document_id IN (
    SELECT id FROM documents
    WHERE filename IN ('getting-started.md', 'api-reference.pdf', 'architecture-overview.md')
);
DELETE FROM documents
WHERE filename IN ('getting-started.md', 'api-reference.pdf', 'architecture-overview.md');

-- Demo documents
INSERT INTO documents (filename, file_path, file_size, processed_at)
VALUES
    ('getting-started.md', '/data/docs/getting-started.md', 2048, NOW()),
    ('api-reference.pdf',  '/data/docs/api-reference.pdf',  15360, NOW()),
    ('architecture-overview.md', '/data/docs/architecture-overview.md', 4096, NOW());

-- Demo chunks
INSERT INTO document_chunks (document_id, chunk_index, content)
SELECT d.id, 0, 'Welcome to the Nexus platform. This guide helps you get started with the system.'
FROM documents d WHERE d.filename = 'getting-started.md';

INSERT INTO document_chunks (document_id, chunk_index, content)
SELECT d.id, 1, 'Nexus provides a unified API for document ingestion, vector search, and LLM-powered query processing.'
FROM documents d WHERE d.filename = 'getting-started.md';

INSERT INTO document_chunks (document_id, chunk_index, content)
SELECT d.id, 0, 'The API reference documents all available endpoints including /documents/upload, /query, and /health.'
FROM documents d WHERE d.filename = 'api-reference.pdf';

INSERT INTO document_chunks (document_id, chunk_index, content)
SELECT d.id, 0, 'The system uses a microservices architecture with PostgreSQL/pgvector for vector storage and Redis for caching.'
FROM documents d WHERE d.filename = 'architecture-overview.md';

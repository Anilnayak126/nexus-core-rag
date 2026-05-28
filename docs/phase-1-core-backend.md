# Phase 1: Core Backend & Vector Storage

## Overview

Phase 1 establishes the RAG (Retrieval-Augmented Generation) foundation: document ingestion, vector embedding, and similarity search powered by PostgreSQL + pgvector.

## Architecture Flow

```mermaid
flowchart LR
  User[User] --> Upload[POST /documents/upload]
  User --> Query[POST /query]
  Upload --> Ingestion[DocumentIngestionPipeline]
  Ingestion --> Extract[PDF Text Extraction<br/>PyMuPDF]
  Extract --> Chunk[Sliding Window Chunking<br/>chunk_size=1000, overlap=200]
  Chunk --> Embed[sentence-transformers<br/>all-MiniLM-L6-v2]
  Embed --> Store[pgvector<br/>document_chunks]
  Query --> Vectorize[Embed Query → vector]
  Vectorize --> Search[HNSW Cosine Similarity]
  Search --> Cache{Redis Cache}
  Cache -->|Hit| Return[Return Cached]
  Cache -->|Miss| Format[LangChain PromptTemplate]
  Format --> Answer[Return Answer + Sources]
```

## Day-by-Day Breakdown

### Days 1-2: Docker & PostgreSQL + pgvector

**Files:** `docker-compose.dev.yml`, `backend/Dockerfile.dev`, `.env.dev`

- PostgreSQL 15 with `ankane/pgvector:latest` for vector extension support
- Redis 7 for semantic caching
- FastAPI with hot-reload on port 8002
- pgAdmin for database admin on port 5051

**Key config in `docker-compose.dev.yml`:**
```yaml
vector_db:
  image: ankane/pgvector:latest
  environment:
    POSTGRES_DB: nexus_knowledge
    POSTGRES_USER: admin
    POSTGRES_PASSWORD: supersecretpassword
```

### Days 3-4: Document Ingestion Pipeline

**File:** `backend/app/llm/document_ingestion.py`  
**Endpoint:** `POST /documents/upload`

#### Flow:

1. **Receive PDF** → saved to `data/` directory
2. **Text extraction** via PyMuPDF (`fitz`) — per-page text extraction
3. **Sliding Window chunking** — splits text into overlapping word-based chunks:
   - `chunk_size`: 1000 words (configurable)
   - `chunk_overlap`: 200 words (configurable)
   - Stride = `chunk_size - chunk_overlap` = 800 words
4. **Embedding generation** via `sentence-transformers/all-MiniLM-L6-v2` (384-dimension vectors)
5. **Storage** in pgvector `document_chunks` table with HNSW index

#### Database Schema:

```sql
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT,
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP
);

CREATE TABLE document_chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id),
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(384),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_chunk_embedding
ON document_chunks
USING hnsw (embedding vector_cosine_ops);
```

#### Chunking Algorithm (sliding window):

```python
for i in range(0, len(words), chunk_size - chunk_overlap):
    chunk = ' '.join(words[i:i + chunk_size])
```

### Days 5-7: Query Processing Pipeline

**Files:**
- `backend/app/llm/query_processing.py` — orchestrates the query flow
- `backend/app/llm/vector_embedding.py` — vector search + Redis caching

**Endpoint:** `POST /query`

#### Flow:

1. **Receive query** (question + optional `top_k`, `confidence_threshold`)
2. **Check Redis cache** — if identical query exists, return cached result
3. **Embed query** using the same `sentence-transformers/all-MiniLM-L6-v2` model
4. **pgvector cosine similarity search** via HNSW index:
   ```sql
   SELECT dc.content, d.filename,
          1 - (dc.embedding <=> $1) as similarity
   FROM document_chunks dc
   JOIN documents d ON dc.document_id = d.id
   ORDER BY dc.embedding <=> $1
   LIMIT $2
   ```
5. **Filter by confidence threshold** (default: 0.7)
6. **Format prompt** using LangChain `PromptTemplate`:
   ```
   You are a helpful AI assistant...
   Context: {retrieved_chunks}
   Question: {user_query}
   Instructions: ... Keep under 1000 tokens
   ```
7. **Return** answer, sources, confidence score, processing time
8. **Cache result** in Redis (TTL: 1 hour) for subsequent identical queries

### Pipeline Initialization (startup)

**File:** `backend/app/main.py`

On application startup, both pipelines are initialized:

```python
@app.on_event("startup")
async def startup_event():
    # 1. Document ingestion pipeline
    document_pipeline = DocumentIngestionPipeline(
        db_url=settings.DATABASE_URL,
        embedding_model_name=settings.EMBEDDING_MODEL,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    await document_pipeline.initialize()
    # Creates asyncpg pool + pgvector tables + HNSW index

    # 2. Query processing pipeline
    query_pipeline = QueryProcessingPipeline(
        db_url=settings.DATABASE_URL,
        redis_url=settings.REDIS_URL,
        llm_config={"model": settings.LLM_MODEL, ...},
        embedding_model_name=settings.EMBEDDING_MODEL,
        confidence_threshold=settings.similarity_threshold,
    )
    await query_pipeline.initialize()
    # Creates asyncpg pool + connects to Redis
```

## Configuration

All settings in `backend/app/core/config.py`:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://admin:...@vector_db:5432/nexus_knowledge` | Postgres connection |
| `REDIS_URL` | `redis://redis:6379` | Redis connection |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model |
| `LLM_MODEL` | `meta-llama/Llama-2-7b-chat-hf` | LLM for answer generation |
| `chunk_size` | `1000` | Words per chunk |
| `chunk_overlap` | `200` | Overlap between chunks |
| `similarity_threshold` | `0.7` | Minimum cosine similarity |

## Running

```bash
make dev-up
# or
docker compose -f docker-compose.dev.yml --env-file .env.dev up -d --build
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/documents/upload` | Upload PDF → extract → chunk → embed → store |
| `POST` | `/query` | Query → vectorize → search → prompt → respond |
| `GET` | `/health` | Health check |
| `GET` | `/metrics` | Query metrics (total, avg time, error rate) |
| `POST` | `/evaluate` | Run evaluation against golden dataset |

## Seed Data

```bash
make dev-seed
```

Inserts 3 demo documents and 5 chunks into pgvector for immediate testing.

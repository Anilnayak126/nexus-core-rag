# System Architecture

```mermaid
flowchart TB
    Client[Client / curl]
    LB[FastAPI Server<br/>port 8002]
    Ingestion[Document Ingestion<br/>PyMuPDF + sliding window]
    Embedding[sentence-transformers<br/>all-MiniLM-L6-v2]
    Query[Query Processing<br/>Semantic Cache + Retrieval Gate]
    PG[(pgvector<br/>PostgreSQL 16 + vector extension<br/>port 5434)]
    Redis[(Redis<br/>port 6380)]
    MLflow[MLflow Tracking<br/>port 5001]
    PgAdmin[pgAdmin<br/>port 5051]

    subgraph Docker["Docker Compose (dev)"]
        direction TB
        Ingestion
        Embedding
        Query
        PG
        Redis
        PgAdmin
    end

    Client -->|POST /documents/upload| LB
    Client -->|POST /query| LB
    Client -->|GET /metrics| LB
    Client -->|GET /health| LB

    LB --> Ingestion
    LB --> Query

    Ingestion --> Embedding
    Ingestion --> PG

    Query --> Embedding
    Query --> PG
    Query --> Redis
    Query --> MLflow

    style LB fill:#4A90D9,color:#fff
    style PG fill:#50C878,color:#fff
    style Redis fill:#DC382D,color:#fff
    style MLflow fill:#FF8C00,color:#fff
    style Embedding fill:#FFD700,color:#000
```

## Container Summary

| Service | Image | Internal Port | Host Port | Purpose |
|---------|-------|---------------|-----------|---------|
| `api` | `nexus-api` | 8000 | 8002 | FastAPI application |
| `vector-db` | `ankane/pgvector` | 5432 | 5434 | PostgreSQL + vector extension |
| `redis` | `redis:7-alpine` | 6379 | 6380 | Caching (semantic + exact) |
| `pgadmin` | `dpage/pgadmin4` | 80 | 5051 | Database admin UI |

## Data Flow

1. **Document Upload**: PDF → PyMuPDF text extraction → cleaning → sliding-window chunking → sentence-transformers embedding → pgvector storage
2. **Query**: JSON question → embedding → 2-level Redis cache check (semantic + exact) → pgvector HNSW cosine search → dedup → confidence calc → Retrieval Gate → formatted answer → MLflow telemetry
3. **Production**: Add `docker-compose.prod.yml` with MLflow, load balancer, and non-reload uvicorn

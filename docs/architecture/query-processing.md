# Query Processing Pipeline

```mermaid
flowchart TB
    User((User))
    API[[/query]]
    Embed[sentence-transformers]
    CacheHit{Level 1 Cache<br/>cos &gt;= 0.95}
    ExactCache{Level 2 Cache<br/>Exact hash match}
    VectorDB[(pgvector<br/>HNSW cos search)]
    Dedup[Deduplicate<br/>filename + chunk_index]
    Confidence[Calculate Confidence]
    Gate{Retrieval Gate<br/>min 0.5}
    Format[Format Answer]
    Response[Return JSON]
    Block[Block: No context found]
    Metrics[Log to MLflow]

    User -->|POST /query| API
    API --> Embed

    Embed -->|query vector| CacheHit
    CacheHit -->|HIT| Format
    CacheHit -->|MISS| ExactCache

    ExactCache -->|HIT| Format
    ExactCache -->|MISS| VectorDB

    VectorDB -->|top k results| Dedup
    Dedup -->|unique chunks| Confidence
    Confidence -->|score| Gate

    Gate -->|passed| Format
    Gate -->|blocked| Block

    Format --> Response
    Block --> Response

    API --> Metrics
    Response -->|200 OK| User

    style API fill:#4A90D9,color:#fff
    style VectorDB fill:#50C878,color:#fff
    style Gate fill:#FF6B6B,color:#fff
    style Embed fill:#FFD700,color:#000
```

## Key Details

| Step | Technology | Notes |
|------|-----------|-------|
| Query Embedding | `sentence-transformers/all-MiniLM-L6-v2` | Same model used for document embedding |
| Level 1 Cache | Redis (semantic) | Cosine similarity >= 0.95 on query embedding |
| Level 2 Cache | Redis (exact) | `hash(query)` key match |
| Vector Search | pgvector `<=>` cosine distance | HNSW index for fast ANN search |
| Deduplication | Python `set()` | By `(filename, chunk_index)`, keeps highest sim |
| Confidence | Weighted avg → sigmoid | `1 / (1 + exp(-weighted_avg))` |
| Retrieval Gate | Threshold check | Blocks if confidence < 0.5 or no chunks |

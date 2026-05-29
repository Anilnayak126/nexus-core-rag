# Semantic Caching

```mermaid
flowchart LR
    Query[User Query]
    Embed[sentence-transformers]
    ExactKey[hash(query)]
    SemanticKey[Store embedding]
    Redis[(Redis)]
    Compare{Cos sim >= 0.95?}
    Return[Return Cached Result]
    Miss[Cache Miss → Vector Search]
    Store[Cache Result<br/>TTL: 3600s]

    Query -->|Level 1| Embed
    Embed --> SemanticKey
    SemanticKey --> Redis
    Redis -->|fetch stored embeddings| Compare
    Compare -->|yes| Return
    Compare -->|no| ExactKey
    ExactKey --> Redis
    Redis -->|fetch exact match| ExactKey
    ExactKey -->|hit| Return
    ExactKey -->|miss| Miss
    Miss -->|after vector search| Store
    Store --> Redis

    style Redis fill:#DC382D,color:#fff
    style Embed fill:#FFD700,color:#000
    style Compare fill:#FFA500,color:#000
```

## Cache Hierarchy

| Level | Key Pattern | Lookup | Threshold |
|-------|------------|--------|-----------|
| 1 — Semantic | `semantic_cache:<hash>` | Cosine similarity against stored query embeddings | >= 0.95 |
| 2 — Exact | `search:<hash(query)>:<top_k>` | Exact string match | Exact |
| Query Result | `query:<hash(query)>` | Exact string match (full result) | Exact |

## Redis Keys

```
search:-649191163085575582:5      → vector search results for query hash + top_k
query:-649191163085575582         → full query response (answer + sources)
semantic_cache:-8378896101063663074 → query embedding + results for semantic matching
```

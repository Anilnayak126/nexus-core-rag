# Semantic Caching

```mermaid
flowchart LR
    Query[User Query]
    Embed[sentence-transformers]
    Level1{Level 1<br/>Semantic<br/>cos &gt;= 0.95}
    Level2{Level 2<br/>Exact hash}
    Redis[(Redis Cache)]
    Cached[Return Cached Result]
    Miss[Cache Miss<br/>Vector Search]
    Store[Store Result<br/>TTL 3600s]

    Query -->|embeds| Embed
    Embed -->|query vector| Level1
    Level1 -->|HIT| Cached
    Level1 -->|MISS| Level2
    Level2 -->|HIT| Cached
    Level2 -->|MISS| Miss
    Miss -->|results| Store
    Store --> Redis
    Redis --> Level1
    Redis --> Level2

    style Redis fill:#DC382D,color:#fff
    style Embed fill:#FFD700,color:#000
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

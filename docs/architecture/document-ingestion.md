# Document Ingestion Pipeline

```mermaid
flowchart TB
    User((User))
    PDF[PDF File]
    API[FastAPI /documents/upload]
    Store[Store on Disk]
    Extract[PyMuPDF Text Extraction]
    Clean[Text Cleaning<br/>Remove non-printable chars]
    Chunk[Sliding Window Chunking<br/>chunk_size=1000, overlap=200]
    Embed[sentence-transformers<br/>all-MiniLM-L6-v2]
    DB[(pgvector<br/>document_chunks)]
    Upsert[Upsert: ON CONFLICT filename]

    User -->|POST /documents/upload| API
    API -->|Save file| Store
    Store --> Extract
    Extract --> Clean
    Clean --> Chunk
    Chunk -->|Store chunks| DB
    Chunk --> Embed
    Embed -->|Store 384-d vector| DB
    DB --> Upsert
    Upsert -->|Return doc_id| API
    API -->|200 OK| User

    style API fill:#4A90D9,color:#fff
    style DB fill:#50C878,color:#fff
    style Embed fill:#FFD700,color:#000
```

## Key Details

| Step | Technology | Notes |
|------|-----------|-------|
| Text Extraction | PyMuPDF (`fitz`) | Extracts text from all PDF pages |
| Text Cleaning | Custom `str.isprintable()` filter | Strips U+FFFD replacement chars while preserving `\n\r\t` |
| Chunking | Sliding Window | Words-based, configurable `chunk_size` and `chunk_overlap` |
| Embedding | `sentence-transformers/all-MiniLM-L6-v2` | 384-dimensional vectors |
| Storage | pgvector | HNSW index with `vector_cosine_ops` |
| Idempotency | `ON CONFLICT (filename) DO UPDATE` | Re-uploading the same file replaces chunks + re-embeds |

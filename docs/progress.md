# Nexus Knowledge Engine — Project Progress

> **Branch:** `feature/phase-3-cicd-mlops`  
> **Updated:** 2026-05-29

---

## Phase 1 — Core Backend & Vector Storage ✅ *Complete*

### What's Built

| Feature | Files | Status |
|---------|-------|--------|
| FastAPI app with CORS, health endpoint | `backend/app/main.py` | ✅ |
| pgvector + Redis + pgAdmin Docker stack | `docker-compose.dev.yml` | ✅ |
| PDF ingestion (PyMuPDF extraction + text cleaning) | `backend/app/llm/document_ingestion.py` | ✅ |
| Sliding window chunking (1000/200) | `backend/app/llm/document_ingestion.py` | ✅ |
| sentence-transformers embeddings (384-d) | `backend/app/llm/vector_embedding.py` | ✅ |
| pgvector HNSW cosine similarity search | `backend/app/llm/vector_embedding.py` | ✅ |
| Document upsert by filename (idempotent uploads) | `backend/app/llm/document_ingestion.py` | ✅ |
| Unique index on `documents(filename)` | `backend/app/llm/document_ingestion.py` | ✅ |

### What's Left

Nothing — Phase 1 is complete.

---

## Phase 2 — LLMOps & Production Safety ✅ *Complete*

### What's Built

| Feature | Files | Status |
|---------|-------|--------|
| Two-level semantic caching (exact hash + embedding) | `backend/app/llm/vector_embedding.py` | ✅ |
| Redis cache with TTL | `redis` service in compose | ✅ |
| Retrieval Gate (min confidence 0.5) | `backend/app/llm/retrieval_gate.py` | ✅ |
| Source deduplication by `(filename, chunk_index)` | `backend/app/llm/query_processing.py` | ✅ |
| `/metrics` endpoint with gate stats | `backend/app/main.py` | ✅ |
| MLflow telemetry (graceful connection handling) | `backend/app/ml/mlflow_client.py` | ✅ |
| Weighted confidence scoring with sigmoid | `backend/app/llm/query_processing.py` | ✅ |
| Configurable thresholds via settings | `backend/app/core/config.py` | ✅ |

### What's Left

Nothing — Phase 2 is complete.

---

## Phase 3 — CI/CD & MLOps ✅ *Complete (deploy on hold)*

### What's Built

| Feature | Files | Status |
|---------|-------|--------|
| Golden dataset (15 test cases) | `data/golden_dataset.json` | ✅ |
| Automated evaluation runner | `backend/scripts/run_evaluation.py` | ✅ |
| Pytest suite (health, upload, query, gate, metrics) | `backend/tests/test_*.py` | ✅ |
| Coverage config (threshold 80%) | `backend/.coveragerc` | ✅ |
| pytest-cov integration | `backend/requirements.txt` | ✅ |
| GitHub Actions CI pipeline | `.github/workflows/ci.yml` | ✅ |
| Multi-stage Dockerfile (builder + runtime) | `backend/Dockerfile.prod` | ✅ |
| `make test`, `make eval`, `make build-prod` targets | `Makefile` | ✅ |
| Phase 3 documentation | `docs/phase/phase-3-cicd-mlops.md` | ✅ |

### What's on Hold

| Feature | Reason | When |
|---------|--------|------|
| AWS ECR image push | User plans to use ECR later | Future |
| AWS ECS Fargate deploy | Auto-deploy on hold | Future |

---

## Upcoming Phases (Not Started)

### Phase 4 — Agentic AI & Multi-Turn Reasoning

| Task | Description |
|------|-------------|
| Conversation memory | Maintain session context across queries |
| Follow-up question handling | Resolve ambiguous references ("what about...") |
| Query decomposition | Break complex questions into sub-queries |
| Agentic retrieval | LLM decides when/ what to retrieve |

### Phase 5 — Advanced RAG & Production Hardening

| Task | Description |
|------|-------------|
| Hybrid search | BM25 + vector (sparse + dense) |
| Re-ranking | Cross-encoder for improved relevance |
| Query expansion | Generate multiple query variants |
| Rate limiting | Protect API from abuse |
| Auth & RBAC | API key or JWT authentication |
| Async ingestion | Background task queue for large docs |

### Phase 6 — Monitoring, Observability & Scaling

| Task | Description |
|------|-------------|
| Prometheus + Grafana dashboards | Query latency, error rates, cache hit rates |
| Structured logging (JSON) | Log aggregation ready |
| Horizontal scaling | Multiple API replicas behind load balancer |
| Database connection pooling tuning | Optimize asyncpg pool size |
| CDN for static assets | If frontend is added |

---

## Quick Reference

### Branches

| Branch | Purpose |
|--------|---------|
| `develop` | Integration branch for active work |
| `main` | Production-ready releases |
| `feature/phase-3-cicd-mlops` | Current Phase 3 work |
| `feature/documentation-overhaul` | Previous docs + cleanup work |

### Key Files

| File | Purpose |
|------|---------|
| `backend/app/main.py` | FastAPI entry point, 4 routes |
| `backend/app/core/config.py` | All settings (DB, Redis, MLflow, thresholds) |
| `backend/app/llm/document_ingestion.py` | PDF → text → chunks → embeddings → pgvector |
| `backend/app/llm/query_processing.py` | Query pipeline: cache → search → gate → answer |
| `docker-compose.dev.yml` | Dev stack (api, vector-db, redis, pgadmin) |
| `Makefile` | `dev-up`, `logs-dev`, `test`, `eval`, `build-prod` |
| `.github/workflows/ci.yml` | CI: lint → test (coverage >= 80%) → eval |
| `data/golden_dataset.json` | 15 Q&A pairs for accuracy evaluation |

### Thresholds (from `config.py`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `similarity_threshold` | 0.6 | Min cosine similarity for chunk inclusion |
| `semantic_cache_threshold` | 0.95 | Min cosine similarity for semantic cache hit |
| `retrieval_gate_min_confidence` | 0.5 | Min confidence to pass retrieval gate |
| `chunk_size` | 1000 | Sliding window chunk size (words) |
| `chunk_overlap` | 200 | Overlap between chunks |

### Docker Compose Services

| Service | Image | Internal Port | Host Port |
|---------|-------|---------------|-----------|
| `api` | `nexus-api` | 8000 | 8002 |
| `vector-db` | `ankane/pgvector` | 5432 | 5434 |
| `redis` | `redis:7-alpine` | 6379 | 6380 |
| `pgadmin` | `dpage/pgadmin4` | 80 | 5051 |

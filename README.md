<div align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&height=180&color=0:111827,100:6366f1&text=Nexus%20Knowledge%20Engine&fontColor=ffffff&fontSize=44&fontAlignY=36" alt="Nexus Knowledge Engine banner" />

  <p><strong>A production-grade RAG backend for enterprise knowledge retrieval with LLMOps capabilities.</strong></p>

  <p>
    <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
    <img src="https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white" alt="Python" />
    <img src="https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=111827" alt="React" />
    <img src="https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL" />
    <img src="https://img.shields.io/badge/pgvector-0.7-4169E1?logo=postgresql&logoColor=white" alt="pgvector" />
    <img src="https://img.shields.io/badge/Redis-7-FF4438?logo=redis&logoColor=white" alt="Redis" />
    <img src="https://img.shields.io/badge/MLflow-2.16-0194E2?logo=mlflow&logoColor=white" alt="MLflow" />
    <img src="https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white" alt="Docker Compose" />
  </p>
</div>

## Overview

Nexus Knowledge Engine is a full-stack RAG (Retrieval-Augmented Generation) system where users can upload documents, generate vector embeddings, query a knowledge base, and track experiments with MLflow. The backend is a FastAPI Python API backed by PostgreSQL with pgvector, Redis caching, and MLflow for LLMOps.

## Project Links

| Area | Path | Purpose |
| --- | --- | --- |
| Dev environment | [`docker-compose.dev.yml`](docker-compose.dev.yml) | Runs API, PostgreSQL + pgvector, Redis, and pgAdmin |
| Prod environment | [`docker-compose.prod.yml`](docker-compose.prod.yml) | Production stack with Nginx, MLflow, and frontend |
| Backend source | [`backend/`](backend/) | FastAPI application with API routes, services, and ML integration |
| AI pipelines | [`backend/app/llm/`](backend/app/llm/) | Document ingestion, vector embedding, and query processing |
| MLflow tracking | [`mlflow/`](mlflow/) | Experiment runs, registered models, and artifacts |
| Project structure | [`project-structure.md`](project-structure.md) | Detailed directory tree and component descriptions |

## Tech Stack

| Layer | Tools |
| --- | --- |
| Frontend | React 18, Vite 5 (planned) |
| Backend | Python 3.11, FastAPI 0.115, Uvicorn, SQLAlchemy 2.0 |
| Database | PostgreSQL 15 with pgvector extension |
| Vector search | pgvector HNSW indexes for cosine similarity |
| Caching | Redis 7 for query result caching |
| LLMOps | MLflow 2.16 for experiment tracking and model versioning |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| DevOps | Docker, Docker Compose, `.env` configuration |

## Feature Guide

| Feature | Backend area | Notes |
| --- | --- | --- |
| Document ingestion | `DocumentIngestion` | PDF text extraction, chunking, and storage |
| Vector embedding | `VectorEmbedding` | Generate and store 384-dimension embeddings in pgvector |
| Query processing | `QueryProcessing` | Similarity search with confidence scoring |
| LLM integration | `config.py`, `llm/` | Configurable LLM models for answer generation |
| MLflow tracking | `mlflow_client.py` | Experiment logging, model versioning, and evaluation |
| Document management | `document_service.py` | Upload, list, view, and delete documents |
| Evaluation | `evaluation_service.py` | Golden dataset testing with metrics |
| Health monitoring | `/health` endpoint | System health check for container orchestration |

## Architecture

```mermaid
flowchart LR
  Client[Client / Frontend] --> API[FastAPI Backend]
  API --> PG[(PostgreSQL + pgvector)]
  API --> Redis[(Redis Cache)]
  API --> MLflow[MLflow Tracking]
  API --> LLM[LLM Service]
  PG --> Chunks[document_chunks - vector(384) HNSW]
  PG --> Docs[documents - metadata & timestamps]
```

## Project Structure

```text
nexus/
  ai/                           -- AI/ML components (models, pipelines, RAG)
  backend/
    app/
      api/routes/               -- FastAPI route handlers
      core/                     -- Config, security, exceptions
      db/                       -- SQLAlchemy models and session
      llm/                      -- Document ingestion, embeddings, query pipeline
      ml/                       -- MLflow client integration
      services/                 -- Business logic layer
      main.py                   -- Application entry point
    tests/                      -- Backend test suite
    scripts/                    -- Utility scripts (seed data, etc.)
  config/                       -- YAML configuration files
  frontend/                     -- React frontend (placeholder)
  mlops/                        -- MLflow experiment data
  scripts/                      -- Setup and deployment scripts
  tests/                        -- Integration and e2e tests
  docs/                         -- API, deployment, development docs
  docker-compose.dev.yml
  docker-compose.prod.yml
  Makefile
  README.md
```

## Quick Start With Docker

From the repository root:

```bash
make dev-up
```

Or manually:

```bash
docker compose -f docker-compose.dev.yml --env-file .env.dev up -d --build
```

Open these URLs:

| Service | URL |
| --- | --- |
| API docs (Swagger) | http://localhost:8002/docs |
| pgAdmin | http://localhost:5051 |
| Redis insight | http://localhost:6380 |
| MLflow UI | http://localhost:5001 |

Stop the stack:

```bash
make dev-down
```

## Environment Setup

Copy the example file before running on a new machine:

```bash
cp .env.example .env
```

Secrets belong in `.env` files only. Do not commit real `DATABASE_URL`, `SECRET_KEY`, or MLflow credentials.

## Important Environment Values

| File | Key | Purpose |
| --- | --- | --- |
| `.env` or `.env.dev` | `DATABASE_URL` | PostgreSQL connection string |
| `.env` or `.env.dev` | `REDIS_URL` | Redis connection string |
| `.env` or `.env.dev` | `EMBEDDING_MODEL` | Sentence transformer model name |
| `.env` or `.env.dev` | `LLM_MODEL` | LLM model identifier |
| `.env` or `.env.dev` | `MLFLOW_TRACKING_URI` | MLflow server URI |

## Docker Services

| Service | Image/build | Port | Description |
| --- | --- | --- | --- |
| `api` | `./backend` (Dockerfile.dev) | `8002:8000` | FastAPI application with hot-reload |
| `vector_db` | `ankane/pgvector` | `5434:5432` | PostgreSQL with pgvector extension |
| `redis` | `redis:7-alpine` | `6380:6379` | Query result cache |
| `pgadmin` | `dpage/pgadmin4` | `5051:80` | PostgreSQL admin UI |

## Common Commands

| Task | Command |
| --- | --- |
| Full dev bootstrap | `make dev-up` |
| Start without rebuild | `make up-dev` |
| Stop (preserve volumes) | `make down-dev` |
| Full destroy | `make dev-down` |
| View logs | `make logs-dev` |
| Seed test data | `make dev-seed` |
| Build API image | `docker compose -f docker-compose.dev.yml build api` |
| Run API container | `docker compose -f docker-compose.dev.yml run api` |

## API Summary

All API endpoints are served at `http://localhost:8002` in dev mode. Interactive documentation is available at `/docs`.

| Domain | Base path | Examples |
| --- | --- | --- |
| Health | `/health` | `GET /health` |
| Documents | `/api/v1/documents` | `POST /upload`, `GET /`, `GET /{id}`, `DELETE /{id}` |
| Query | `/api/v1/query` | `POST /` with question and top_k |
| Evaluation | `/api/v1/evaluate` | `POST /` against golden dataset |
| Metrics | `/api/v1/metrics` | `GET /` system metrics |

## Local Development Without Docker

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The Docker flow is the recommended path because it aligns PostgreSQL with pgvector, Redis, MLflow, and runtime settings.

## Security Notes

- `.env` and `.env.dev` files are ignored by git.
- Database credentials and API keys must never be committed.
- Use `DEBUG=False` and production credentials before deploying publicly.
- MLflow tracking URI should point to a secured server in production.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| Port conflicts (5050, 8002, etc.) | Change host port in `docker-compose.dev.yml` |
| API cannot connect to database | Confirm `DATABASE_URL` uses `vector_db` as hostname |
| pgAdmin login fails | Default: `admin@admin.com` / `password` |
| Vector search returns no results | Ensure documents are processed and embeddings are generated |
| Seed data not applied | Run `make dev-seed` or `docker exec nexus-vector-db psql -U admin -d nexus_knowledge < backend/scripts/seed_test_data.sql` |

# Nexus Knowledge Engine - Project Structure

```
nexus/
├── ai/                              # AI/ML components
│   ├── models/                      # Pre-trained model configs and wrappers
│   ├── pipelines/                   # ML pipelines (shall link to backend/app/llm)
│   ├── evaluation/                  # Evaluation scripts and golden datasets
│   └── rag/                         # RAG-specific retriever/generator logic
│
├── backend/                         # FastAPI backend
│   ├── app/
│   │   ├── api/routes/              # API endpoint handlers
│   │   ├── core/                    # Config, security, exceptions
│   │   ├── db/                      # SQLAlchemy models and session
│   │   ├── llm/                     # Document ingestion, embeddings, query pipeline
│   │   ├── ml/                      # MLflow client integration
│   │   ├── services/                # Business logic layer
│   │   └── main.py                  # FastAPI application entry point
│   ├── tests/                       # Backend unit/integration tests
│   ├── scripts/                     # Utility scripts (seed data, migrations)
│   ├── Dockerfile.dev               # Dev image with hot-reload
│   ├── Dockerfile.prod              # Production image
│   └── requirements.txt             # Python dependencies
│
├── config/                          # YAML/TOML configuration files
│   └── mlflow_config.yml            # MLflow experiment and model settings
│
├── mlops/                           # MLflow experiment tracking data
│   └── mlflow_config.yml            # (mirrored from config/)
│
├── frontend/                        # React frontend (placeholder)
│
├── scripts/                         # Root-level dev/prod scripts
│   └── setup.sh                     # Local virtual environment setup
│
├── tests/                           # Integration and e2e tests
│   ├── integration/
│   └── e2e/
│
├── docs/                            # Documentation
│   ├── api/
│   ├── deployment/
│   └── development/
│
├── docker-compose.dev.yml           # Dev environment (PostgreSQL, Redis, pgAdmin)
├── docker-compose.prod.yml          # Production stack (Nginx, MLflow, frontend)
├── Makefile                         # Dev workflow commands
├── .env.dev                         # Dev environment variables
├── .gitignore                       # Git ignore rules
├── project-structure.md             # This file
└── README.md                        # Project README
```

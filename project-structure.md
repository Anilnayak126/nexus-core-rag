# Nexus Knowledge Engine - Project Structure

```
nexus/
├── ai/                          # AI/ML related components
│   ├── models/                  # Pre-trained models and configurations
│   │   ├── embedding_models/
│   │   ├── llm_models/
│   │   └── evaluation_models/
│   ├── pipelines/               # ML pipelines for data processing
│   │   ├── document_ingestion.py
│   │   ├── vector_embedding.py
│   │   └── query_processing.py
│   ├── evaluation/              # Evaluation scripts and metrics
│   │   ├── golden_dataset/
│   │   ├── metrics.py
│   │   └── benchmarking.py
│   └── rag/                      # RAG-specific components
│       ├── retriever.py
│       └── generator.py
│
├── mlflow/                      # MLflow experiment tracking
│   ├── experiments/             # Experiment runs
│   ├── models/                  # Registered models
│   └── artifacts/               # Artifacts and datasets
│
├── backend/                     # FastAPI backend
│   ├── app/
│   │   ├── api/                 # API endpoints
│   │   │   ├── v1/
│   │   │   │   ├── documents.py
│   │   │   │   ├── queries.py
│   │   │   │   ├── evaluation.py
│   │   │   │   └── health.py
│   │   ├── core/                # Core application logic
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── exceptions.py
│   │   ├── db/                  # Database models and operations
│   │   │   ├── connection.py
│   │   │   ├── session.py
│   │   │   └── models.py
│   │   ├── ml/                  # ML integration
│   │   │   ├── embedding_service.py
│   │   │   ├── llm_service.py
│   │   │   └── mlflow_client.py
│   │   ├── services/             # Business logic services
│   │   │   ├── document_service.py
│   │   │   ├── query_service.py
│   │   │   └── evaluation_service.py
│   │   └── main.py
│   ├── tests/                   # Backend tests
│   └── scripts/                 # Backend scripts
│
├── frontend/                    # React frontend
│   ├── src/
│   │   ├── components/          # Reusable components
│   │   ├── pages/               # Page components
│   │   ├── services/            # API services
│   │   ├── utils/               # Utility functions
│   │   ├── types/               # TypeScript types
│   │   └── main.tsx
│   └── public/                  # Static assets
│
├── docker/                      # Docker configurations
│   ├── backend/
│   │   ├── Dockerfile.dev
│   │   └── Dockerfile.prod
│   └── nginx/                   # Nginx configuration
│       └── nginx.conf
│
├── config/                      # Configuration files
│   ├── mlflow_config.yml
│   ├── logging_config.yml
│   ├── database_config.yml
│   └── model_configs/
│
├── scripts/                     # Utility scripts
│   ├── setup.sh
│   ├── deploy.sh
│   └── evaluate.sh
│
├── tests/                      # Integration and e2e tests
│   ├── integration/
│   └── e2e/
│
├── docs/                        # Documentation
│   ├── api/
│   ├── deployment/
│   └── development/
│
├── docker-compose.dev.yml       # Development environment
├── docker-compose.prod.yml      # Production environment
├── .env.example                # Environment variables example
├── .gitignore                  # Git ignore file
├── README.md                   # Project README
└── requirements.txt            # Python dependencies
```

## Key Features

### AI/ML Components:
- **Modular AI pipeline architecture** for easy model swapping
- **Vector embeddings** with pgvector for efficient similarity search
- **LLM integration** with configurable models
- **Evaluation framework** with golden dataset testing
- **MLflow integration** for experiment tracking

### LLMOps Features:
- **Automated model evaluation** pipeline
- **Prompt versioning** and management
- **Drift detection** with confidence thresholds
- **Observability** with metrics and logging
- **CI/CD integration** for ML model deployment

### Infrastructure:
- **Containerized** with Docker for consistent environments
- **Scalable architecture** with Redis caching
- **Production-ready** with Nginx reverse proxy
- **Database** with PostgreSQL and pgvector extension
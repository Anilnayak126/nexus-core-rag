# Nexus Knowledge Engine - Backend API

A production-grade RAG (Retrieval-Augmented Generation) system backend for enterprise knowledge retrieval with LLMOps capabilities.

## 🚀 Overview

The Nexus Knowledge Engine is a sophisticated backend API that provides:
- **Document Processing**: PDF ingestion, text chunking, and vector embedding generation
- **Intelligent Querying**: Vector similarity search with confidence scoring
- **LLMOps Integration**: MLflow experiment tracking, model versioning, and evaluation
- **Production-Ready**: Containerized architecture with Redis caching and PostgreSQL vector storage

## 🏗️ Architecture

```
nexus/
├── ai/                          # AI/ML related components
│   ├── models/                  # Pre-trained models and configurations
│   ├── pipelines/               # ML pipelines for data processing
│   │   ├── document_ingestion.py
│   │   ├── vector_embedding.py
│   │   └── query_processing.py
│   ├── evaluation/              # Evaluation scripts and metrics
│   └── rag/                      # RAG-specific components
├── backend/                     # FastAPI backend
│   ├── app/
│   │   ├── api/                 # API endpoints
│   │   ├── core/                # Core application logic
│   │   ├── db/                  # Database models and operations
│   │   ├── ml/                  # ML integration
│   │   └── services/             # Business logic services
│   ├── tests/                   # Backend tests
│   └── scripts/                 # Backend scripts
├── mlflow/                      # MLflow experiment tracking
├── config/                      # Configuration files
├── docker/                      # Docker configurations
├── scripts/                     # Utility scripts
├── tests/                      # Integration and e2e tests
└── docs/                        # Documentation
```

## 🛠️ Features

### Core Functionality
- **Document Ingestion**: Process PDF documents with text extraction and chunking
- **Vector Embeddings**: Generate and store embeddings using sentence transformers
- **Similarity Search**: Efficient vector similarity search with pgvector
- **Query Processing**: Retrieve relevant content and generate answers
- **Confidence Scoring**: Automated confidence threshold handling

### LLMOps Features
- **MLflow Integration**: Complete experiment tracking and model management
- **Automated Evaluation**: Golden dataset testing with comprehensive metrics
- **Model Versioning**: Track and manage different model versions
- **Performance Monitoring**: Real-time metrics and alerting
- **Drift Detection**: Monitor model performance and data drift

### Production Features
- **Containerized**: Docker and Docker Compose for consistent environments
- **Caching**: Redis for improved response times
- **Database**: PostgreSQL with pgvector extension
- **Monitoring**: Comprehensive logging and metrics collection
- **Scalable**: Designed for horizontal scaling

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- PostgreSQL
- Redis
- MLflow (optional)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd nexus
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Start services with Docker Compose**
   ```bash
   docker-compose -f docker-compose.dev.yml up -d
   ```

5. **Initialize the database**
   ```bash
   python scripts/init_db.py
   ```

### Development Setup

1. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

2. **Install development dependencies**
   ```bash
   pip install -r requirements-dev.txt
   ```

3. **Run development server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## 📚 API Documentation

### Endpoints

#### Document Management
- `POST /api/v1/documents/upload` - Upload and process a document
- `GET /api/v1/documents` - List all documents
- `GET /api/v1/documents/{document_id}` - Get document details
- `DELETE /api/v1/documents/{document_id}` - Delete a document

#### Query Processing
- `POST /api/v1/query` - Process a query and get answer
- `GET /api/v1/metrics` - Get system metrics
- `GET /api/v1/health` - Health check

#### Evaluation
- `POST /api/v1/evaluate` - Run evaluation against golden dataset

### Example Usage

#### Upload Document
```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@document.pdf"
```

#### Query Knowledge Base
```bash
curl -X POST "http://localhost:8000/api/v1/query" \
     -H "Content-Type: application/json" \
     -d '{
       "question": "What is the purpose of this system?",
       "top_k": 5,
       "confidence_threshold": 0.7
     }'
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection URL | `postgresql://postgres:postgres@localhost:5432/nexus_db` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` |
| `MLFLOW_TRACKING_URI` | MLflow tracking URI | `http://localhost:5001` |
| `EMBEDDING_MODEL` | Embedding model name | `sentence-transformers/all-MiniLM-L6-v2` |
| `LLM_MODEL` | LLM model name | `meta-llama/Llama-2-7b-chat-hf` |

### MLflow Configuration

Edit `config/mlflow_config.yml` to customize:
- Experiment settings
- Model configurations
- Evaluation thresholds
- Monitoring parameters

## 🧪 Testing

### Run Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_documents.py
```

### Integration Tests
```bash
# Run integration tests
pytest tests/integration/
```

## 📊 Monitoring & Observability

### MLflow UI
Access the MLflow UI at `http://localhost:5001` to:
- Track experiments
- Compare model performance
- View model artifacts
- Register and manage models

### System Metrics
The system collects various metrics:
- Query response times
- Confidence scores
- Document processing metrics
- Error rates
- Cache hit ratios

### Logging
Logs are structured and can be sent to:
- Console (development)
- File (production)
- ELK Stack (enterprise)
- Cloud logging services

## 🚀 Deployment

### Development
```bash
docker-compose -f docker-compose.dev.yml up -d
```

### Production
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Environment Variables for Production
```bash
# Required production variables
POSTGRES_USER=your_postgres_user
POSTGRES_PASSWORD=your_postgres_password
ECR_REPOSITORY=your_ecr_repository
MLFLOW_BACKEND_URI=your_mlflow_backend_uri
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

### Development Guidelines
- Follow PEP 8 style guidelines
- Write comprehensive docstrings
- Include unit tests for new features
- Update documentation as needed

## 📈 Performance Optimization

### Caching Strategy
- Redis for query results
- Embedding vector caching
- Document chunk caching

### Database Optimization
- Proper indexing for vector search
- Connection pooling
- Query optimization

### Model Optimization
- Model quantization
- Batch processing
- Asynchronous inference

## 🔒 Security

### API Security
- Input validation
- Rate limiting
- Authentication (JWT/OAuth)
- CORS protection

### Data Security
- Encryption at rest
- Secure file handling
- Access controls

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Issues**
   - Check PostgreSQL is running
   - Verify connection URL
   - Check network connectivity

2. **Memory Issues**
   - Reduce batch size
   - Increase Redis memory
   - Optimize model loading

3. **Slow Query Performance**
   - Check Redis cache
   - Verify database indexes
   - Monitor system resources

### Debug Mode
Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
```

## 📚 Additional Resources

### Documentation
- [API Documentation](docs/api/)
- [Deployment Guide](docs/deployment/)
- [Development Guide](docs/development/)

### Related Projects
- [Frontend Repository](https://github.com/your-org/nexus-frontend)
- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
- [pgvector Documentation](https://github.com/pgvector/pgvector)

## 🤝 Support

For support and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review the documentation

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
- [MLflow](https://mlflow.org/) for experiment tracking
- [pgvector](https://github.com/pgvector/pgvector) for vector search
- [Sentence Transformers](https://www.sbert.net/) for embeddings

---

Made with ❤️ by the Nexus AI Team
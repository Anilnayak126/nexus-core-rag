# Production Deployment

## Prerequisites
- Docker & Docker Compose
- ECR repository for backend image
- PostgreSQL credentials
- MLflow backend URI

## Steps

1. Set environment variables in `.env`
2. Build and push backend image to ECR
3. Run `docker compose -f docker-compose.prod.yml up -d`

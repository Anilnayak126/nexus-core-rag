import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://admin:supersecretpassword@vector_db:5432/nexus_knowledge"
    
    # Embedding model
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # LLM model
    LLM_MODEL: str = "meta-llama/Llama-2-7b-chat-hf"
    
    # Directories
    data_dir: str = "data"
    models_dir: str = "models"
    
    # Redis
    REDIS_URL: str = "redis://redis:6379"
    
    # MLflow
    MLFLOW_TRACKING_URI: str = "http://localhost:5001"
    
    # API settings
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    chunk_size: int = 1000
    chunk_overlap: int = 200
    
    # Vector search
    similarity_threshold: float = 0.7
    
    class Config:
        env_file = ".env"

settings = Settings()
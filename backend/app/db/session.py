"""
Database connection module for the Nexus Knowledge Engine.

This module sets up the SQLAlchemy database engine and provides a sessionmaker
dependency that can be injected into FastAPI routes for interacting with the PostgreSQL database.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Import the settings from the config module
from app.core.config import settings

# Create the SQLAlchemy database engine
# The engine is the core interface to the database, responsible for managing the connection pool
# and executing SQL statements.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Automatically checks connections when retrieved from the pool
    pool_recycle=300,    # Recycle connections after 5 minutes to prevent connection issues
    echo=False  # Set to True for SQL query debugging in development
)

# Create a SessionLocal class
# This is a factory for creating new Session objects
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a base class for declarative models
# All database models will inherit from this base class
Base = declarative_base()

def get_db() -> Session:
    """
    Dependency function that provides a database session for FastAPI routes.
    
    This function creates a new database session, yields it for use in the route,
    and then closes the session when the request is complete.
    
    Yields:
        Session: A SQLAlchemy database session
        
    Example:
        @app.get("/items/")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        # Ensure the session is closed after the request is complete
        db.close()

def init_db() -> None:
    """
    Initialize the database by creating all tables.
    
    This function creates all tables defined in the models if they don't already exist.
    It should be called when the application starts up.
    """
    # Import all models here to ensure they are registered with SQLAlchemy
    # This is necessary for the Base.metadata.create_all() to work properly
    from app.services.document_service import Document
    from app.services.vector_service import VectorEmbedding
    
    # Create all tables in the database
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully.")
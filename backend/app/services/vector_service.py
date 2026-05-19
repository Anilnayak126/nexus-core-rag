import numpy as np
from typing import List, Dict
import asyncpg
import logging
from sentence_transformers import SentenceTransformer
from app.config import settings

logger = logging.getLogger(__name__)

class VectorService:
    def __init__(self):
        self.model = None
        self.pool = None
    
    async def initialize(self):
        """Initialize embeddings model and database connection"""
        # Load embedding model
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
        
        # Create database connection pool
        self.pool = await asyncpg.create_pool(
            settings.DATABASE_URL,
            min_size=5,
            max_size=20
        )
        
        # Create vector extension and tables if not exists
        await self._create_tables()
    
    async def _create_tables(self):
        """Create database tables for vector storage"""
        async with self.pool.acquire() as conn:
            # Create vector extension
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            
            # Create documents table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    filename TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Create document_chunks table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id SERIAL PRIMARY KEY,
                    document_id INTEGER REFERENCES documents(id),
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding VECTOR(384),  # Adjust based on model
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Create index for similarity search
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunk_embedding 
                ON document_chunks 
                USING hnsw (embedding vector_cosine_ops)
            """)
    
    async def store_document_chunks(self, file_path: str, chunks: List[str]):
        """Store document chunks with embeddings in database"""
        async with self.pool.acquire() as conn:
            # Get or create document record
            document_id = await conn.fetchval(
                "INSERT INTO documents (filename) VALUES ($1) RETURNING id",
                os.path.basename(file_path)
            )
            
            # Generate embeddings and store chunks
            embeddings = self.model.encode(chunks)
            
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                await conn.execute(
                    """
                    INSERT INTO document_chunks 
                    (document_id, chunk_index, content, embedding)
                    VALUES ($1, $2, $3, $4)
                    """,
                    document_id,
                    i,
                    chunk,
                    embedding.tolist()
                )
    
    async def search_similar_chunks(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search for similar chunks using cosine similarity"""
        # Generate query embedding
        query_embedding = self.model.encode([query])[0]
        
        async with self.pool.acquire() as conn:
            # Perform vector similarity search
            results = await conn.fetch(
                """
                SELECT 
                    dc.content,
                    d.filename,
                    1 - (dc.embedding <=> $1) as similarity
                FROM document_chunks dc
                JOIN documents d ON dc.document_id = d.id
                ORDER BY dc.embedding <=> $1
                LIMIT $2
                """,
                query_embedding.tolist(),
                top_k
            )
            
            return [
                {
                    "content": row["content"],
                    "filename": row["filename"],
                    "similarity": float(row["similarity"])
                }
                for row in results
            ]
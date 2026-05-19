"""
Vector Embedding Pipeline for Nexus Knowledge Engine

This pipeline handles:
1. Generation of embeddings for text chunks
2. Similarity search using vector operations
3. Embedding management and storage
"""

import numpy as np
import logging
from typing import List, Dict, Optional, Tuple
import asyncpg
from sentence_transformers import SentenceTransformer
from dataclasses import dataclass
import time
import redis
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Data class for search results"""
    content: str
    filename: str
    similarity: float
    chunk_index: int

class VectorEmbeddingPipeline:
    """
    Pipeline for managing vector embeddings and similarity search.
    """
    
    def __init__(
        self,
        db_url: str,
        redis_url: str,
        embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        cache_ttl: int = 3600,
        similarity_threshold: float = 0.7
    ):
        """
        Initialize the vector embedding pipeline.
        
        Args:
            db_url: Database connection URL
            redis_url: Redis connection URL for caching
            embedding_model_name: Name of the embedding model
            cache_ttl: Cache time-to-live in seconds
            similarity_threshold: Minimum similarity threshold for results
        """
        self.db_url = db_url
        self.pool = None
        self.redis_client = None
        self.embedding_model = SentenceTransformer(embedding_model_name)
        self.cache_ttl = cache_ttl
        self.similarity_threshold = similarity_threshold
        self.model_name = embedding_model_name
        
    async def initialize(self):
        """Initialize database and Redis connections."""
        # Initialize database
        self.pool = await asyncpg.create_pool(
            self.db_url,
            min_size=5,
            max_size=20
        )
        
        # Initialize Redis
        self.redis_client = redis.from_url(self.redis_url)
        
        # Verify connections
        await self.redis_client.ping()
        
    async def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a given text.
        
        Args:
            text: Input text
            
        Returns:
            Text embedding vector
        """
        return self.embedding_model.encode(text)
    
    async def search_similar_chunks(
        self, 
        query: str, 
        top_k: int = 5,
        use_cache: bool = True
    ) -> List[SearchResult]:
        """
        Search for chunks similar to the query.
        
        Args:
            query: Search query
            top_k: Number of results to return
            use_cache: Whether to use Redis cache
            
        Returns:
            List of search results
        """
        # Create cache key
        cache_key = f"search:{hash(query)}:{top_k}"
        
        # Check cache
        if use_cache:
            cached_result = await self.redis_client.get(cache_key)
            if cached_result:
                logger.info(f"Cache hit for query: {query}")
                return [SearchResult(**r) for r in json.loads(cached_result)]
        
        # Generate query embedding
        query_embedding = await self.generate_embedding(query)
        
        # Perform similarity search
        results = await self._vector_search(query_embedding, top_k)
        
        # Cache results
        if use_cache and results:
            await self.redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps([r.__dict__ for r in results])
            )
        
        return results
    
    async def _vector_search(
        self, 
        query_embedding: np.ndarray, 
        top_k: int
    ) -> List[SearchResult]:
        """
        Perform vector similarity search in the database.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            
        Returns:
            List of search results
        """
        async with self.pool.acquire() as conn:
            # Perform similarity search
            results = await conn.fetch(
                """
                SELECT 
                    dc.content,
                    d.filename,
                    1 - (dc.embedding <=> $1) as similarity,
                    dc.chunk_index
                FROM document_chunks dc
                JOIN documents d ON dc.document_id = d.id
                ORDER BY dc.embedding <=> $1
                LIMIT $2
                """,
                query_embedding.tolist(),
                top_k
            )
            
            # Filter by similarity threshold
            filtered_results = [
                SearchResult(
                    content=row["content"],
                    filename=row["filename"],
                    similarity=float(row["similarity"]),
                    chunk_index=row["chunk_index"]
                )
                for row in results
                if float(row["similarity"]) >= self.similarity_threshold
            ]
            
            return filtered_results
    
    async def get_document_chunks(self, document_id: int) -> List[Dict]:
        """
        Get all chunks for a specific document.
        
        Args:
            document_id: Document ID
            
        Returns:
            List of document chunks
        """
        async with self.pool.acquire() as conn:
            results = await conn.fetch(
                """
                SELECT chunk_index, content, embedding
                FROM document_chunks
                WHERE document_id = $1
                ORDER BY chunk_index
                """,
                document_id
            )
            
            return [
                {
                    "chunk_index": row["chunk_index"],
                    "content": row["content"],
                    "embedding": row["embedding"]
                }
                for row in results
            ]
    
    async def get_similar_documents(self, query: str, threshold: float = 0.7) -> List[Dict]:
        """
        Get documents similar to the query.
        
        Args:
            query: Search query
            threshold: Similarity threshold
            
        Returns:
            List of similar documents with similarity scores
        """
        # Get similar chunks
        chunks = await self.search_similar_chunks(query, top_k=10)
        
        # Group by document
        doc_scores = {}
        for chunk in chunks:
            if chunk.similarity >= threshold:
                if chunk.filename not in doc_scores:
                    doc_scores[chunk.filename] = []
                doc_scores[chunk.filename].append(chunk.similarity)
        
        # Calculate average scores
        result = []
        for doc, scores in doc_scores.items():
            avg_score = sum(scores) / len(scores)
            result.append({
                "filename": doc,
                "similarity": avg_score,
                "chunks": len(scores)
            })
        
        # Sort by similarity
        result.sort(key=lambda x: x["similarity"], reverse=True)
        
        return result
    
    async def rebuild_cache(self) -> int:
        """
        Rebuild the embedding cache for all documents.
        
        Returns:
            Number of cached documents
        """
        logger.info("Starting cache rebuild...")
        
        # Get all documents
        async with self.pool.acquire() as conn:
            documents = await conn.fetch(
                "SELECT id, filename FROM documents WHERE processed_at IS NOT NULL"
            )
        
        # Cache embeddings for each document
        cached_count = 0
        for doc in documents:
            try:
                chunks = await self.get_document_chunks(doc["id"])
                if chunks:
                    # Cache document embeddings
                    cache_key = f"doc_embeddings:{doc['id']}"
                    await self.redis_client.setex(
                        cache_key,
                        self.cache_ttl,
                        json.dumps(chunks)
                    )
                    cached_count += 1
            except Exception as e:
                logger.error(f"Error caching document {doc['filename']}: {str(e)}")
        
        logger.info(f"Cache rebuild complete. Cached {cached_count} documents.")
        return cached_count
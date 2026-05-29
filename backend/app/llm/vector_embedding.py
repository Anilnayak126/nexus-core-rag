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
import redis.asyncio as redis
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
        self.redis_url = redis_url
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
        use_cache: bool = True,
        semantic_cache_threshold: float = 0.95,
    ) -> List[SearchResult]:
        """
        Search for chunks similar to the query.

        Uses a two-level cache:
          1. Semantic cache — compares query embedding against past query
             embeddings stored in Redis. If a semantically similar query
             (cosine >= semantic_cache_threshold) exists, returns its results.
          2. Exact cache — hash-based lookup for repeated identical queries.

        Args:
            query: Search query
            top_k: Number of results to return
            use_cache: Whether to use Redis cache
            semantic_cache_threshold: Minimum cosine similarity for a semantic hit

        Returns:
            List of search results
        """
        query_embedding = await self.generate_embedding(query)

        # --- Level 1: Semantic cache ---
        if use_cache:
            semantic_hit = await self._check_semantic_cache(
                query_embedding, semantic_cache_threshold
            )
            if semantic_hit is not None:
                logger.info("Semantic cache HIT (similarity=%.3f)", semantic_hit["similarity"])
                return [SearchResult(**r) for r in semantic_hit["results"]]

        # --- Level 2: Exact (hash-based) cache ---
        cache_key = f"search:{hash(query)}:{top_k}"
        if use_cache:
            cached_result = await self.redis_client.get(cache_key)
            if cached_result:
                logger.info("Exact cache hit for query: %s", query)
                return [SearchResult(**r) for r in json.loads(cached_result)]

        # --- Miss: perform vector search ---
        results = await self._vector_search(query_embedding, top_k)

        # Cache results
        if use_cache and results:
            await self.redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps([r.__dict__ for r in results])
            )
            # Also store in semantic cache for future similar queries
            await self._store_semantic_cache(query_embedding, results)

        return results

    async def _check_semantic_cache(
        self, query_embedding: np.ndarray, threshold: float
    ) -> Optional[dict]:
        """Check Redis for a semantically similar past query."""
        cached_keys = await self.redis_client.keys("semantic_cache:*")
        if not cached_keys:
            return None

        query_vec = query_embedding.flatten()
        best_match = None
        best_sim = 0.0

        for key in cached_keys:
            raw = await self.redis_client.get(key)
            if not raw:
                continue
            entry = json.loads(raw)
            stored_vec = np.array(entry["embedding"], dtype=np.float32)
            sim = np.dot(query_vec, stored_vec) / (
                np.linalg.norm(query_vec) * np.linalg.norm(stored_vec)
            )
            if sim > best_sim:
                best_sim = sim
                best_match = entry

        if best_match and best_sim >= threshold:
            return {"similarity": float(best_sim), "results": best_match["results"]}
        return None

    async def _store_semantic_cache(
        self, query_embedding: np.ndarray, results: List[SearchResult]
    ):
        """Store query embedding + results for future semantic lookups."""
        key = f"semantic_cache:{hash(str(results))}"
        entry = {
            "embedding": query_embedding.flatten().tolist(),
            "results": [r.__dict__ for r in results],
            "cached_at": time.time(),
        }
        await self.redis_client.setex(key, self.cache_ttl, json.dumps(entry))
    
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
                str(query_embedding.tolist()),
                top_k
            )
            
            # Filter by similarity threshold
            filtered_results = [
                SearchResult(
                    content=row["content"],
                    filename=row["filename"],
                    similarity=float(row["similarity"]) if row["similarity"] is not None else 0.0,
                    chunk_index=row["chunk_index"]
                )
                for row in results
                if row["similarity"] is not None
                and float(row["similarity"]) >= self.similarity_threshold
            ]
            
            return filtered_results

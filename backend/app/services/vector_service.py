from app.core.config import settings
import numpy as np
import redis.asyncio as redis
import pickle
import logging
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class VectorService:
    def __init__(self):
        self.redis_client = None
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
    
    async def initialize(self):
        """Initialize the vector service"""
        try:
            # Connect to Redis
            self.redis_client = redis.from_url(settings.REDIS_URL)
            await self.redis_client.ping()
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.error(f"Error connecting to Redis: {str(e)}")
            raise
    
    async def store_document_chunks(self, file_path: str, chunks: List[str]):
        """Store document chunks and their embeddings in Redis"""
        if not self.redis_client:
            raise RuntimeError("Vector service not initialized")
        
        try:
            # Generate embeddings for all chunks
            embeddings = self.model.encode(chunks)
            
            # Store in Redis
            document_key = f"doc:{file_path}"
            
            # Store chunks and embeddings
            pipe = self.redis_client.pipeline()
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_key = f"{document_key}:chunk:{i}"
                embedding_key = f"{document_key}:embedding:{i}"
                
                # Store chunk text
                await pipe.hset(chunk_key, mapping={
                    "text": chunk,
                    "file_path": file_path,
                    "chunk_index": str(i)
                })
                
                # Store embedding
                await pipe.set(embedding_key, pickle.dumps(embedding))
            
            await pipe.execute()
            logger.info(f"Stored {len(chunks)} chunks for {file_path}")
            
        except Exception as e:
            logger.error(f"Error storing document chunks: {str(e)}")
            raise
    
    async def search_similar_chunks(
        self, 
        query_embedding: np.ndarray, 
        top_k: int = 5, 
        threshold: float = 0.7
    ) -> List[Dict]:
        """Search for similar chunks using Redis"""
        if not self.redis_client:
            raise RuntimeError("Vector service not initialized")
        
        try:
            # Get all document keys
            doc_keys = await self.redis_client.keys("doc:*:embedding:*")
            
            # Calculate similarities and collect results
            results = []
            
            for embedding_key in doc_keys:
                # Get embedding
                stored_embedding_bytes = await self.redis_client.get(embedding_key)
                if not stored_embedding_bytes:
                    continue
                
                stored_embedding = pickle.loads(stored_embedding_bytes)
                
                # Calculate cosine similarity
                similarity = np.dot(query_embedding, stored_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(stored_embedding)
                )
                
                if similarity >= threshold:
                    # Get corresponding chunk data
                    chunk_key = embedding_key.replace(":embedding:", ":chunk:")
                    chunk_data = await self.redis_client.hgetall(chunk_key)
                    
                    if chunk_data:
                        results.append({
                            "text": chunk_data.get(b"text", b"").decode("utf-8"),
                            "file_path": chunk_data.get(b"file_path", b"").decode("utf-8"),
                            "chunk_index": int(chunk_data.get(b"chunk_index", 0)),
                            "similarity": float(similarity)
                        })
            
            # Sort by similarity and return top_k
            results.sort(key=lambda x: x["similarity"], reverse=True)
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Error searching similar chunks: {str(e)}")
            raise
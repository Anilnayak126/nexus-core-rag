"""
Query Processing Pipeline for Nexus Knowledge Engine

This pipeline handles:
1. Query understanding and preprocessing
2. Retrieval of relevant document chunks
3. Answer generation using LLM
4. Confidence scoring and filtering
"""

import time
import logging
from typing import Dict, List, Optional
import json
from dataclasses import dataclass
import asyncpg
from sentence_transformers import SentenceTransformer
from .vector_embedding import VectorEmbeddingPipeline
import redis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class QueryResult:
    """Data class for query results"""
    answer: str
    sources: List[Dict]
    confidence: float
    processing_time: float
    query_id: str
    timestamp: float

@dataclass
class QueryMetrics:
    """Data class for query metrics"""
    total_queries: int
    average_response_time: float
    error_rate: float
    average_confidence: float
    top_queries: List[Dict]

class QueryProcessingPipeline:
    """
    Pipeline for processing user queries and generating answers.
    """
    
    def __init__(
        self,
        db_url: str,
        redis_url: str,
        llm_config: Dict,
        embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        confidence_threshold: float = 0.7,
        max_tokens: int = 1000,
        temperature: float = 0.1
    ):
        """
        Initialize the query processing pipeline.
        
        Args:
            db_url: Database connection URL
            redis_url: Redis connection URL
            llm_config: LLM configuration
            embedding_model_name: Embedding model name
            confidence_threshold: Minimum confidence threshold
            max_tokens: Maximum tokens for LLM response
            temperature: LLM temperature
        """
        self.db_url = db_url
        self.redis_client = None
        self.llm_config = llm_config
        self.embedding_model = SentenceTransformer(embedding_model_name)
        self.confidence_threshold = confidence_threshold
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.query_id_counter = 0
        
        # Initialize components
        self.vector_pipeline = VectorEmbeddingPipeline(
            db_url=db_url,
            redis_url=redis_url,
            embedding_model_name=embedding_model_name
        )
        
        # Initialize Redis for query caching
        self.redis_client = redis.from_url(redis_url)
        
    async def initialize(self):
        """Initialize pipeline components."""
        await self.vector_pipeline.initialize()
        
    async def process_query(self, query: str, user_id: Optional[str] = None) -> QueryResult:
        """
        Process a user query and return an answer.
        
        Args:
            query: User query
            user_id: Optional user ID for tracking
            
        Returns:
            Query result with answer and sources
        """
        start_time = time.time()
        query_id = self._generate_query_id()
        
        try:
            # Check cache
            cache_key = f"query:{hash(query)}"
            cached_result = await self.redis_client.get(cache_key)
            
            if cached_result:
                logger.info(f"Cache hit for query: {query}")
                return QueryResult(**json.loads(cached_result))
            
            # Step 1: Retrieve relevant chunks
            relevant_chunks = await self.vector_pipeline.search_similar_chunks(
                query,
                top_k=5
            )
            
            # Step 2: Filter by confidence
            filtered_chunks = [
                chunk for chunk in relevant_chunks
                if chunk.similarity >= self.confidence_threshold
            ]
            
            # Step 3: Generate answer
            if filtered_chunks:
                answer = await self._generate_answer(query, filtered_chunks)
                confidence = self._calculate_confidence(filtered_chunks)
            else:
                answer = "I couldn't find relevant information to answer your question."
                confidence = 0.0
                filtered_chunks = []
            
            # Create result
            result = QueryResult(
                answer=answer,
                sources=[
                    {
                        "content": chunk.content,
                        "filename": chunk.filename,
                        "similarity": chunk.similarity,
                        "chunk_index": chunk.chunk_index
                    }
                    for chunk in filtered_chunks
                ],
                confidence=confidence,
                processing_time=time.time() - start_time,
                query_id=query_id,
                timestamp=time.time()
            )
            
            # Cache result
            await self.redis_client.setex(
                cache_key,
                3600,  # 1 hour cache
                json.dumps(result.__dict__)
            )
            
            # Log query
            await self._log_query(query, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            raise
    
    async def _generate_answer(self, query: str, chunks: List) -> str:
        """
        Generate answer using LLM with retrieved context.
        
        Args:
            query: User query
            chunks: Relevant document chunks
            
        Returns:
            Generated answer
        """
        # Format context
        context = "\n\n".join([
            f"Source {i+1} ({chunk.filename}):\n{chunk.content}"
            for i, chunk in enumerate(chunks)
        ])
        
        # Create prompt
        prompt = self._create_prompt(query, context)
        
        # Here you would integrate with your LLM service
        # For demonstration, we'll return a formatted response
        return self._format_llm_response(query, chunks)
    
    def _create_prompt(self, query: str, context: str) -> str:
        """
        Create prompt for LLM.
        
        Args:
            query: User query
            context: Retrieved context
            
        Returns:
            Formatted prompt
        """
        return f"""You are a helpful AI assistant answering questions based on the provided context.

Context:
{context}

Question: {query}

Instructions:
1. Provide a concise and accurate answer based only on the context provided
2. If the context doesn't contain enough information, say "I don't have enough information to answer this question"
3. Cite the sources you use in your answer
4. Keep your answer under {self.max_tokens} tokens

Answer:
"""
    
    def _format_llm_response(self, query: str, chunks: List) -> str:
        """
        Format LLM response (placeholder implementation).
        
        Args:
            query: User query
            chunks: Relevant chunks
            
        Returns:
            Formatted response
        """
        if not chunks:
            return "I don't have enough information to answer this question."
        
        # Extract key information from chunks
        key_points = []
        for chunk in chunks[:3]:  # Use top 3 chunks
            # Extract sentences that contain important keywords
            sentences = chunk.content.split('. ')
            for sentence in sentences:
                if any(word in sentence.lower() for word in query.lower().split()):
                    key_points.append(sentence.strip())
        
        # Create answer
        answer_parts = [f"Based on the provided context, here's my answer to '{query}':"]
        
        if key_points:
            answer_parts.append("\nKey points from the documents:")
            for point in key_points[:3]:  # Limit to top 3 points
                answer_parts.append(f"• {point}")
        else:
            # Use the most relevant chunk
            best_chunk = chunks[0]
            answer_parts.append(f"\nRelevant information from {best_chunk.filename}:")
            answer_parts.append(best_chunk.content[:500] + "..." if len(best_chunk.content) > 500 else best_chunk.content)
        
        answer_parts.append("\n[Note: This is a demo response. In production, this would be generated by an LLM.]")
        
        return "\n".join(answer_parts)
    
    def _calculate_confidence(self, chunks: List) -> float:
        """
        Calculate confidence score based on retrieved chunks.
        
        Args:
            chunks: Retrieved chunks
            
        Returns:
            Confidence score
        """
        if not chunks:
            return 0.0
        
        # Weighted average based on similarity scores
        weights = [chunk.similarity for chunk in chunks]
        total_weight = sum(weights)
        
        if total_weight == 0:
            return 0.0
        
        # Calculate weighted average
        confidence = sum(w * s for w, s in zip(weights, [c.similarity for c in chunks])) / total_weight
        
        # Apply sigmoid to normalize to 0-1
        return 1 / (1 + np.exp(-confidence))
    
    def _generate_query_id(self) -> str:
        """Generate unique query ID."""
        self.query_id_counter += 1
        return f"q_{int(time.time())}_{self.query_id_counter}"
    
    async def _log_query(self, query: str, result: QueryResult):
        """
        Log query for analytics.
        
        Args:
            query: User query
            result: Query result
        """
        # In production, you would log to a database or analytics system
        log_data = {
            "query": query,
            "timestamp": result.timestamp,
            "processing_time": result.processing_time,
            "confidence": result.confidence,
            "sources_count": len(result.sources),
            "query_id": result.query_id
        }
        
        # Log to Redis for real-time analytics
        await self.redis_client.lpush(
            "query_log",
            json.dumps(log_data)
        )
        
        # Keep only recent logs
        await self.redis_client.ltrim("query_log", 0, 9999)
    
    async def get_query_metrics(self, time_window: int = 24) -> QueryMetrics:
        """
        Get query metrics for a time window.
        
        Args:
            time_window: Time window in hours
            
        Returns:
            Query metrics
        """
        # Get query logs from Redis
        logs = await self.redis_client.lrange("query_log", 0, -1)
        
        if not logs:
            return QueryMetrics(
                total_queries=0,
                average_response_time=0.0,
                error_rate=0.0,
                average_confidence=0.0,
                top_queries=[]
            )
        
        # Parse logs
        query_logs = [json.loads(log) for log in logs]
        
        # Filter by time window
        cutoff_time = time.time() - (time_window * 3600)
        recent_logs = [
            log for log in query_logs
            if log["timestamp"] >= cutoff_time
        ]
        
        if not recent_logs:
            return QueryMetrics(
                total_queries=0,
                average_response_time=0.0,
                error_rate=0.0,
                average_confidence=0.0,
                top_queries=[]
            )
        
        # Calculate metrics
        total_queries = len(recent_logs)
        average_response_time = sum(log["processing_time"] for log in recent_logs) / total_queries
        average_confidence = sum(log["confidence"] for log in recent_logs) / total_queries
        
        # Calculate error rate (queries with very low confidence)
        error_rate = sum(1 for log in recent_logs if log["confidence"] < 0.3) / total_queries
        
        # Get top queries (by frequency)
        query_counts = {}
        for log in recent_logs:
            query = log["query"]
            query_counts[query] = query_counts.get(query, 0) + 1
        
        top_queries = sorted(
            [{"query": q, "count": c} for q, c in query_counts.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:10]
        
        return QueryMetrics(
            total_queries=total_queries,
            average_response_time=average_response_time,
            error_rate=error_rate,
            average_confidence=average_confidence,
            top_queries=top_queries
        )
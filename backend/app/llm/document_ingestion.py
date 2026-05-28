"""
Document Ingestion Pipeline for Nexus Knowledge Engine

This pipeline handles the ingestion of PDF documents, including:
1. Text extraction from PDFs
2. Text chunking with overlap
3. Generation of text embeddings
4. Storage in vector database
"""

import os
import fitz  # PyMuPDF
import logging
from typing import List, Dict, Optional
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer
import asyncio
import asyncpg
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DocumentChunk:
    """Data class for document chunks"""
    content: str
    chunk_index: int
    document_id: int
    embedding: Optional[np.ndarray] = None

class DocumentIngestionPipeline:
    """
    Pipeline for processing and ingesting PDF documents into the knowledge base.
    """
    
    def __init__(
        self,
        db_url: str,
        embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        """
        Initialize the document ingestion pipeline.
        
        Args:
            db_url: Database connection URL
            embedding_model_name: Name of the embedding model to use
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
        """
        self.db_url = db_url
        self.embedding_model = SentenceTransformer(embedding_model_name)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.pool = None
        
    async def initialize(self):
        """Initialize database connection and create tables if needed."""
        self.pool = await asyncpg.create_pool(
            self.db_url,
            min_size=5,
            max_size=20
        )
        
        # Create tables
        async with self.pool.acquire() as conn:
            # Create vector extension
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            
            # Create documents table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size BIGINT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    processed_at TIMESTAMP
                )
            """)
            
            # Create document_chunks table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id SERIAL PRIMARY KEY,
                    document_id INTEGER REFERENCES documents(id),
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding VECTOR(384)
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Create indexes
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunk_embedding 
                ON document_chunks 
                USING hnsw (embedding vector_cosine_ops)
            """)
    
    async def process_document(self, file_path: str) -> Dict:
        """
        Process a single PDF document.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dictionary with processing results
        """
        try:
            # Extract text
            text = await self._extract_text(file_path)
            
            # Create chunks
            chunks = self._create_chunks(text)
            
            # Store in database
            doc_id = await self._store_document(file_path, chunks)
            
            # Generate and store embeddings
            await self._store_embeddings(doc_id, chunks)
            
            logger.info(f"Successfully processed document: {file_path}")
            
            return {
                "document_id": doc_id,
                "filename": os.path.basename(file_path),
                "chunks_processed": len(chunks),
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {str(e)}")
            raise
    
    async def _extract_text(self, file_path: str) -> str:
        """Extract text from PDF file."""
        text = ""
        try:
            with fitz.open(file_path) as doc:
                for page in doc:
                    text += page.get_text()
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {str(e)}")
            raise
        
        return text
    
    def _create_chunks(self, text: str) -> List[str]:
        """Split text into overlapping chunks."""
        chunks = []
        words = text.split()
        
        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk = ' '.join(words[i:i + self.chunk_size])
            chunks.append(chunk)
        
        return chunks
    
    async def _store_document(self, file_path: str, chunks: List[str]) -> int:
        """Store document metadata in database."""
        async with self.pool.acquire() as conn:
            # Get file info
            file_size = os.path.getsize(file_path)
            filename = os.path.basename(file_path)
            
            # Insert document record
            doc_id = await conn.fetchval(
                """
                INSERT INTO documents (filename, file_path, file_size, processed_at)
                VALUES ($1, $2, $3, NOW())
                RETURNING id
                """,
                filename,
                file_path,
                file_size
            )
            
            # Insert chunks
            for i, chunk in enumerate(chunks):
                await conn.execute(
                    """
                    INSERT INTO document_chunks (document_id, chunk_index, content)
                    VALUES ($1, $2, $3)
                    """,
                    doc_id,
                    i,
                    chunk
                )
            
            return doc_id
    
    async def _store_embeddings(self, doc_id: int, chunks: List[str]):
        """Generate and store embeddings for document chunks."""
        # Generate embeddings
        embeddings = self.embedding_model.encode(chunks)
        
        async with self.pool.acquire() as conn:
            # Update chunks with embeddings
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                await conn.execute(
                    """
                    UPDATE document_chunks
                    SET embedding = $1
                    WHERE document_id = $2 AND chunk_index = $3
                    """,
                    embedding.tolist(),
                    doc_id,
                    i
                )
    
    async def batch_process_documents(self, directory: str) -> List[Dict]:
        """
        Process all PDF files in a directory.
        
        Args:
            directory: Directory containing PDF files
            
        Returns:
            List of processing results
        """
        results = []
        pdf_files = list(Path(directory).glob("*.pdf"))
        
        for pdf_file in pdf_files:
            try:
                result = await self.process_document(str(pdf_file))
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing {pdf_file}: {str(e)}")
                results.append({
                    "filename": pdf_file.name,
                    "status": "error",
                    "error": str(e)
                })
        
        return results
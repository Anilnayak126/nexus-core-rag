import os
import fitz  # PyMuPDF
from typing import Dict, List
from app.config import settings
import logging
from app.services.vector_service import VectorService

logger = logging.getLogger(__name__)

class DocumentService:
    def __init__(self):
        self.vector_service = VectorService()
    
    async def process_document(self, file_path: str) -> Dict:
        """Process a PDF document: extract text, chunk, and create embeddings"""
        try:
            # Extract text from PDF
            text = self._extract_text(file_path)
            
            # Create chunks
            chunks = self._create_chunks(text)
            
            # Generate embeddings and store
            await self.vector_service.store_document_chunks(
                file_path=file_path,
                chunks=chunks
            )
            
            return {
                "id": os.path.basename(file_path),
                "chunks": len(chunks),
                "status": "processed"
            }
            
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {str(e)}")
            raise
    
    def _extract_text(self, file_path: str) -> str:
        """Extract text from PDF file"""
        text = ""
        with fitz.open(file_path) as doc:
            for page in doc:
                text += page.get_text()
        return text
    
    def _create_chunks(self, text: str) -> List[str]:
        """Split text into overlapping chunks"""
        chunks = []
        words = text.split()
        
        for i in range(0, len(words), settings.chunk_size - settings.chunk_overlap):
            chunk = ' '.join(words[i:i + settings.chunk_size])
            chunks.append(chunk)
        
        return chunks
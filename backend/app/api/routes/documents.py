"""
Document API endpoints for Nexus Knowledge Engine
"""

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from typing import List, Optional
import os
import logging
from pydantic import BaseModel
from app.core.config import settings
from app.services.document_service import DocumentService
from app.ml.mlflow_client import MLflowClient

router = APIRouter()
logger = logging.getLogger(__name__)

class DocumentResponse(BaseModel):
    message: str
    document_id: str
    chunks_processed: int
    status: str

class DocumentListResponse(BaseModel):
    documents: List[dict]
    total_count: int

@router.post("/documents/upload", response_model=DocumentResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process a document.
    
    Args:
        file: PDF file to upload
        
    Returns:
        Document processing result
    """
    try:
        # Validate file
        if not file.filename.endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are supported"
            )
        
        # Check file size
        file_size = 0
        contents = await file.read()
        file_size = len(contents)
        await file.seek(0)  # Reset file pointer
        
        if file_size > settings.max_file_size:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds maximum limit of {settings.max_file_size} bytes"
            )
        
        # Save file
        file_path = os.path.join(settings.data_dir, file.filename)
        os.makedirs(settings.data_dir, exist_ok=True)
        
        with open(file_path, "wb") as buffer:
            buffer.write(contents)
        
        # Process document
        document_service = DocumentService()
        result = await document_service.process_document(file_path)
        
        # Log to MLflow
        mlflow_client = MLflowClient()
        mlflow_client.log_document_processing(
            filename=file.filename,
            file_size=file_size,
            chunks_processed=result["chunks"]
        )
        
        return DocumentResponse(
            message="Document processed successfully",
            document_id=result["id"],
            chunks_processed=result["chunks"],
            status="processed"
        )
        
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents", response_model=DocumentListResponse)
async def list_documents():
    """
    List all uploaded documents.
    
    Returns:
        List of documents
    """
    try:
        document_service = DocumentService()
        documents = await document_service.get_documents()
        
        return DocumentListResponse(
            documents=documents,
            total_count=len(documents)
        )
        
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/{document_id}")
async def get_document(document_id: str):
    """
    Get document details.
    
    Args:
        document_id: Document ID
        
    Returns:
        Document details
    """
    try:
        document_service = DocumentService()
        document = await document_service.get_document(document_id)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return document
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """
    Delete a document.
    
    Args:
        document_id: Document ID
        
    Returns:
        Deletion result
    """
    try:
        document_service = DocumentService()
        result = await document_service.delete_document(document_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {"message": "Document deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
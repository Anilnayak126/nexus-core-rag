from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from app.services.document_service import DocumentService
from app.services.query_service import QueryService
from app.services.evaluation_service import EvaluationService
from app.services.vector_service import VectorService
from app.core.config import settings

app = FastAPI(
    title="Nexus Knowledge Engine API",
    description="Production-grade RAG system for enterprise knowledge retrieval",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
document_service = DocumentService()
query_service = QueryService()
evaluation_service = EvaluationService()
vector_service = VectorService()

class QueryRequest(BaseModel):
    question: str
    top_k: int = 5
    confidence_threshold: float = 0.7

class QueryResponse(BaseModel):
    answer: str
    sources: List[dict]
    confidence: float
    processing_time: float

class EvaluationRequest(BaseModel):
    dataset_path: str
    run_name: str = "evaluation_run"

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    await vector_service.initialize()

@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and process a document"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    file_path = os.path.join(settings.data_dir, file.filename)
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    
    # Process document
    result = await document_service.process_document(file_path)
    
    return {
        "message": "Document processed successfully",
        "document_id": result["id"],
        "chunks_processed": result["chunks"]
    }

@app.post("/query", response_model=QueryResponse)
async def query_knowledge_base(request: QueryRequest):
    """Query the knowledge base"""
    result = await query_service.query(
        question=request.question,
        top_k=request.top_k,
        confidence_threshold=request.confidence_threshold
    )
    
    return QueryResponse(**result)

@app.post("/evaluate")
async def run_evaluation(request: EvaluationRequest):
    """Run evaluation against golden dataset"""
    results = await evaluation_service.run_evaluation(
        dataset_path=request.dataset_path,
        run_name=request.run_name
    )
    
    return results

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.get("/metrics")
async def get_metrics():
    """Get system metrics"""
    return await query_service.get_metrics()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
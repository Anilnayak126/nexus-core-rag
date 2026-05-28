from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import logging

from app.core.config import settings
from app.llm.document_ingestion import DocumentIngestionPipeline
from app.llm.query_processing import QueryProcessingPipeline, QueryResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Nexus Knowledge Engine API",
    description="Production-grade RAG system for enterprise knowledge retrieval",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

document_pipeline: Optional[DocumentIngestionPipeline] = None
query_pipeline: Optional[QueryProcessingPipeline] = None


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
    global document_pipeline, query_pipeline

    document_pipeline = DocumentIngestionPipeline(
        db_url=settings.DATABASE_URL,
        embedding_model_name=settings.EMBEDDING_MODEL,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    await document_pipeline.initialize()
    logger.info("Document ingestion pipeline initialized")

    query_pipeline = QueryProcessingPipeline(
        db_url=settings.DATABASE_URL,
        redis_url=settings.REDIS_URL,
        llm_config={
            "model": settings.LLM_MODEL,
            "temperature": 0.1,
            "max_tokens": 1000,
        },
        embedding_model_name=settings.EMBEDDING_MODEL,
        confidence_threshold=settings.similarity_threshold,
        max_tokens=1000,
        temperature=0.1,
    )
    await query_pipeline.initialize()
    logger.info("Query processing pipeline initialized")


@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    file_path = os.path.join(settings.data_dir, file.filename)
    os.makedirs(settings.data_dir, exist_ok=True)

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    result = await document_pipeline.process_document(file_path)

    return {
        "message": "Document processed successfully",
        "document_id": result["document_id"],
        "filename": result["filename"],
        "chunks_processed": result["chunks_processed"],
        "status": result["status"],
    }


@app.post("/query", response_model=QueryResponse)
async def query_knowledge_base(request: QueryRequest):
    result: QueryResult = await query_pipeline.process_query(
        query=request.question,
    )

    return QueryResponse(
        answer=result.answer,
        sources=result.sources,
        confidence=result.confidence,
        processing_time=result.processing_time,
    )


@app.post("/evaluate")
async def run_evaluation(request: EvaluationRequest):
    from app.services.evaluation_service import EvaluationService

    service = EvaluationService()
    results = await service.run_evaluation(
        dataset_path=request.dataset_path,
        run_name=request.run_name,
    )
    return results


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/metrics")
async def get_metrics():
    metrics = await query_pipeline.get_query_metrics()
    return {
        "total_queries": metrics.total_queries,
        "average_response_time": metrics.average_response_time,
        "error_rate": metrics.error_rate,
        "average_confidence": metrics.average_confidence,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

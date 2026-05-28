from typing import Dict, List
from app.core.config import settings
from app.services.query_service import QueryService
import logging
import os
import json
import time
from pathlib import Path

logger = logging.getLogger(__name__)

class EvaluationService:
    def __init__(self):
        self.query_service = QueryService()
    
    async def run_evaluation(
        self, 
        dataset_path: str, 
        run_name: str = "evaluation_run"
    ) -> Dict:
        """Run evaluation against golden dataset"""
        try:
            # Load dataset
            with open(dataset_path, 'r') as f:
                dataset = json.load(f)
            
            results = []
            total_questions = len(dataset)
            
            for i, item in enumerate(dataset):
                logger.info(f"Processing question {i+1}/{total_questions}")
                
                # Query the system
                start_time = time.time()
                query_result = await self.query_service.query(
                    question=item["question"],
                    top_k=5,
                    confidence_threshold=0.7
                )
                query_time = time.time() - start_time
                
                # Evaluate result
                evaluation = {
                    "question": item["question"],
                    "expected_answer": item.get("expected_answer", ""),
                    "actual_answer": query_result["answer"],
                    "sources": query_result["sources"],
                    "confidence": query_result["confidence"],
                    "query_time": query_time,
                    "correct": self._check_answer(query_result["answer"], item.get("expected_answer", ""))
                }
                
                results.append(evaluation)
            
            # Calculate metrics
            accuracy = sum(1 for r in results if r["correct"]) / total_questions
            avg_query_time = sum(r["query_time"] for r in results) / total_questions
            
            # Save results
            results_path = Path(settings.data_dir) / "evaluations" / f"{run_name}_results.json"
            results_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(results_path, 'w') as f:
                json.dump({
                    "run_name": run_name,
                    "total_questions": total_questions,
                    "accuracy": accuracy,
                    "avg_query_time": avg_query_time,
                    "results": results
                }, f, indent=2)
            
            return {
                "run_name": run_name,
                "total_questions": total_questions,
                "accuracy": accuracy,
                "avg_query_time": avg_query_time,
                "results_path": str(results_path)
            }
            
        except Exception as e:
            logger.error(f"Error running evaluation: {str(e)}")
            raise
    
    def _check_answer(self, actual: str, expected: str) -> bool:
        """Simple answer checking (can be improved with more sophisticated NLP)"""
        if not expected:
            return True  # No expected answer provided
        
        # Simple substring check (can be improved)
        return expected.lower() in actual.lower()
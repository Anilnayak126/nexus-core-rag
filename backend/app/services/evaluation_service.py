import json
import logging
from typing import Dict, List
from app.config import settings
from app.services.query_service import QueryService

logger = logging.getLogger(__name__)

class EvaluationService:
    def __init__(self):
        self.query_service = QueryService()
    
    async def run_evaluation(self, dataset_path: str, run_name: str) -> Dict:
        """Run evaluation against golden dataset"""
        try:
            # Load golden dataset
            golden_dataset = self._load_dataset(dataset_path)
            
            # Evaluate each question
            results = []
            total_questions = len(golden_dataset)
            
            for i, item in enumerate(golden_dataset):
                logger.info(f"Evaluating question {i+1}/{total_questions}")
                
                result = await self._evaluate_question(item)
                results.append(result)
            
            # Calculate metrics
            metrics = self._calculate_metrics(results)
            
            return {
                "run_name": run_name,
                "total_questions": total_questions,
                "metrics": metrics,
                "detailed_results": results
            }
            
        except Exception as e:
            logger.error(f"Error running evaluation: {str(e)}")
            raise
    
    def _load_dataset(self, dataset_path: str) -> List[Dict]:
        """Load golden dataset from JSON file"""
        with open(dataset_path, 'r') as f:
            return json.load(f)
    
    async def _evaluate_question(self, item: Dict) -> Dict:
        """Evaluate a single question"""
        question = item["question"]
        expected_answer = item["expected_answer"]
        
        # Get system response
        response = await self.query_service.query(question)
        
        # Calculate metrics
        answer_similarity = self._calculate_similarity(response["answer"], expected_answer)
        retrieval_accuracy = self._check_retrieval_accuracy(response["sources"], item.get("relevant_docs", []))
        
        return {
            "question": question,
            "expected_answer": expected_answer,
            "actual_answer": response["answer"],
            "answer_similarity": answer_similarity,
            "retrieval_accuracy": retrieval_accuracy,
            "confidence": response["confidence"],
            "processing_time": response["processing_time"],
            "sources_count": len(response["sources"])
        }
    
    def _calculate_similarity(self, answer1: str, answer2: str) -> float:
        """Calculate similarity between two answers"""
        # Simple implementation - in production, use more sophisticated metrics
        # like BLEU, ROUGE, or BERTScore
        words1 = set(answer1.lower().split())
        words2 = set(answer2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def _check_retrieval_accuracy(self, retrieved_docs: List[Dict], relevant_docs: List[str]) -> float:
        """Check if retrieved documents are relevant"""
        if not relevant_docs:
            return 1.0 if not retrieved_docs else 0.0
        
        retrieved_filenames = {doc["filename"] for doc in retrieved_docs}
        relevant_set = set(relevant_docs)
        
        intersection = retrieved_filenames.intersection(relevant_set)
        return len(intersection) / len(relevant_set)
    
    def _calculate_metrics(self, results: List[Dict]) -> Dict:
        """Calculate overall evaluation metrics"""
        if not results:
            return {}
        
        answer_similarity = sum(r["answer_similarity"] for r in results) / len(results)
        retrieval_accuracy = sum(r["retrieval_accuracy"] for r in results) / len(results)
        avg_confidence = sum(r["confidence"] for r in results) / len(results)
        avg_processing_time = sum(r["processing_time"] for r in results) / len(results)
        
        return {
            "average_answer_similarity": answer_similarity,
            "average_retrieval_accuracy": retrieval_accuracy,
            "average_confidence": avg_confidence,
            "average_processing_time": avg_processing_time,
            "total_questions": len(results)
        }
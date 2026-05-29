"""
MLflow Client for Nexus Knowledge Engine
"""

import mlflow
import mlflow.pytorch
import mlflow.sklearn
import mlflow.transformers
import numpy as np
import logging
from typing import Dict, List, Optional, Any
import json
import os
from datetime import datetime
from app.core.config import settings

logger = logging.getLogger(__name__)

class MLflowClient:
    """
    MLflow client for experiment tracking and model management.
    """
    
    def __init__(self, tracking_uri: Optional[str] = None, experiment_name: str = "nexus_knowledge_engine"):
        """
        Initialize MLflow client.

        Args:
            tracking_uri: MLflow tracking URI
            experiment_name: Experiment name (defaults to nexus_knowledge_engine)
        """
        self.tracking_uri = tracking_uri or settings.MLFLOW_TRACKING_URI
        self._connected = False
        try:
            mlflow.set_tracking_uri(self.tracking_uri)
            # Test connection
            mlflow.get_experiment_by_name("_test_connection")
            self._connected = True
        except Exception as e:
            logger.warning("MLflow not available at %s: %s", self.tracking_uri, e)

        self.experiment_name = experiment_name

    def _safe_call(self, fn, *args, **kwargs):
        """Execute an MLflow call safely — skip if not connected."""
        if not self._connected:
            return
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            logger.debug("MLflow call skipped: %s", e)

    def get_or_create_experiment(self, experiment_name: str = None) -> Optional[str]:
        """Get or create an experiment."""
        if not self._connected:
            return None
        experiment_name = experiment_name or self.experiment_name
        
        try:
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if experiment is None:
                experiment_id = mlflow.create_experiment(experiment_name)
                logger.info("Created new experiment: %s (ID: %s)", experiment_name, experiment_id)
            else:
                experiment_id = experiment.experiment_id
                logger.info("Using existing experiment: %s (ID: %s)", experiment_name, experiment_id)
            
            return experiment_id
            
        except Exception as e:
            logger.debug("MLflow experiment error: %s", e)
            return None
    
    def start_run(self, run_name: str = None, experiment_name: str = None):
        """Start an MLflow run."""
        if not self._connected:
            return None
        experiment_id = self.get_or_create_experiment(experiment_name)
        if not experiment_id:
            return None
        
        try:
            run = mlflow.start_run(
                experiment_id=experiment_id,
                run_name=run_name,
                tags={"project": "nexus", "created_at": datetime.now().isoformat()}
            )
            return run
        except Exception as e:
            logger.debug("MLflow start_run skipped: %s", e)
            return None
    
    def log_document_processing(self, filename: str, file_size: int, chunks_processed: int):
        """Log document processing metrics."""
        if not self._connected:
            return
        run = self.start_run(f"document_processing_{filename.replace('.', '_')}")
        if not run:
            return
        try:
            mlflow.log_param("filename", filename)
            mlflow.log_param("file_size", file_size)
            mlflow.log_metric("chunks_processed", chunks_processed)
            mlflow.log_metric("processing_efficiency", chunks_processed / (file_size / 1024))
        finally:
            mlflow.end_run()
            
    def log_query_metrics(self, query: str, response_time: float, confidence: float, 
                         sources_count: int, error: bool = False):
        """Log query metrics."""
        if not self._connected:
            return
        run = self.start_run(f"query_{hash(query)}")
        if not run:
            return
        try:
            mlflow.log_param("query_length", len(query))
            mlflow.log_param("query_words", len(query.split()))
            mlflow.log_metric("response_time", response_time)
            mlflow.log_metric("confidence", confidence)
            mlflow.log_metric("sources_count", sources_count)
            mlflow.log_metric("error", int(error))
            mlflow.log_param("query_category", self._categorize_query(query))
        finally:
            mlflow.end_run()
    
    def log_retrieval_gate_event(self, query: str, confidence: float,
                                  threshold: float, reason: str):
        """Log a retrieval gate block event."""
        if not self._connected:
            return
        run = self.start_run("retrieval_gate_blocked")
        if not run:
            return
        try:
            mlflow.log_param("query_length", len(query))
            mlflow.log_param("query_words", len(query.split()))
            mlflow.log_metric("gate_confidence", confidence)
            mlflow.log_param("gate_threshold", threshold)
            mlflow.log_param("gate_reason", reason)
        finally:
            mlflow.end_run()

    def log_evaluation_metrics(self, evaluation_name: str, metrics: Dict[str, float]):
        """Log evaluation metrics."""
        run = self.start_run(f"evaluation_{evaluation_name}")
        if not run:
            return
        try:
            for key, value in metrics.items():
                mlflow.log_metric(key, value)
        finally:
            mlflow.end_run()
    
    def log_model_performance(self, model_name: str, performance_metrics: Dict[str, float]):
        """
        Log model performance metrics.
        
        Args:
            model_name: Model name
            performance_metrics: Performance metrics
        """
        with self.start_run(f"model_performance_{model_name}") as run:
            for key, value in performance_metrics.items():
                mlflow.log_metric(key, value)
    
    def log_embedding_generation(self, text_length: int, embedding_time: float, 
                               embedding_dimension: int):
        """Log embedding generation metrics."""
        run = self.start_run("embedding_generation")
        if not run:
            return
        try:
            mlflow.log_param("text_length", text_length)
            mlflow.log_metric("embedding_time", embedding_time)
            mlflow.log_param("embedding_dimension", embedding_dimension)
            mlflow.log_metric("tokens_per_second", text_length / embedding_time)
        finally:
            mlflow.end_run()
    
    def log_system_metrics(self, total_queries: int, average_response_time: float,
                          error_rate: float, active_documents: int):
        """Log system-wide metrics."""
        run = self.start_run("system_metrics")
        if not run:
            return
        try:
            mlflow.log_metric("total_queries", total_queries)
            mlflow.log_metric("average_response_time", average_response_time)
            mlflow.log_metric("error_rate", error_rate)
            mlflow.log_metric("active_documents", active_documents)
        finally:
            mlflow.end_run()
    
    def save_model(self, model, model_name: str, artifact_path: str = None):
        """
        Save a model to MLflow.
        
        Args:
            model: Model to save
            model_name: Name for the model
            artifact_path: Path to save artifacts
        """
        try:
            with self.start_run(f"model_save_{model_name}") as run:
                mlflow.sklearn.log_model(
                    sk_model=model,
                    artifact_path=artifact_path or model_name,
                    registered_model_name=model_name
                )
                logger.info(f"Saved model: {model_name}")
                
        except Exception as e:
            logger.error(f"Error saving model: {str(e)}")
            raise
    
    def load_model(self, model_name: str, version: str = "latest"):
        """
        Load a model from MLflow.
        
        Args:
            model_name: Model name
            version: Model version
            
        Returns:
            Loaded model
        """
        try:
            model_uri = f"models:/{model_name}/{version}"
            model = mlflow.sklearn.load_model(model_uri)
            logger.info(f"Loaded model: {model_name} (version: {version})")
            return model
            
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            raise
    
    def get_experiment_runs(self, experiment_name: str = None) -> List[Dict]:
        """
        Get all runs for an experiment.
        
        Args:
            experiment_name: Experiment name
            
        Returns:
            List of runs
        """
        experiment_name = experiment_name or self.experiment_name
        
        try:
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if experiment is None:
                return []
            
            runs = mlflow.search_runs(
                experiment_ids=[experiment.experiment_id],
                output_format="list"
            )
            
            return [run.to_dict() for run in runs]
            
        except Exception as e:
            logger.error(f"Error getting experiment runs: {str(e)}")
            raise
    
    def get_model_versions(self, model_name: str) -> List[Dict]:
        """
        Get all versions of a model.
        
        Args:
            model_name: Model name
            
        Returns:
            List of model versions
        """
        try:
            client = mlflow.MlflowClient()
            versions = client.search_model_versions(f"name='{model_name}'")
            
            return [version.to_dict() for version in versions]
            
        except Exception as e:
            logger.error(f"Error getting model versions: {str(e)}")
            raise
    
    def _categorize_query(self, query: str) -> str:
        """
        Categorize a query based on keywords.
        
        Args:
            query: User query
            
        Returns:
            Query category
        """
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["what", "define", "explain"]):
            return "explanatory"
        elif any(word in query_lower for word in ["how", "steps", "process"]):
            return "procedural"
        elif any(word in query_lower for word in ["compare", "difference", "versus"]):
            return "comparison"
        elif any(word in query_lower for word in ["why", "reason", "because"]):
            return "reasoning"
        else:
            return "factual"
    
    def create_evaluation_report(self, experiment_name: str = None) -> Dict:
        """
        Create a comprehensive evaluation report.
        
        Args:
            experiment_name: Experiment name
            
        Returns:
            Evaluation report
        """
        experiment_name = experiment_name or self.experiment_name
        
        try:
            runs = self.get_experiment_runs(experiment_name)
            
            if not runs:
                return {"error": "No runs found for experiment"}
            
            # Calculate metrics
            metrics = {}
            for run in runs:
                for key, value in run.get("data", {}).get("metrics", {}).items():
                    if key not in metrics:
                        metrics[key] = []
                    metrics[key].append(value)
            
            # Calculate averages
            avg_metrics = {}
            for key, values in metrics.items():
                avg_metrics[key] = sum(values) / len(values)
            
            # Create report
            report = {
                "experiment_name": experiment_name,
                "total_runs": len(runs),
                "metrics_summary": avg_metrics,
                "run_details": runs,
                "generated_at": datetime.now().isoformat()
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error creating evaluation report: {str(e)}")
            raise
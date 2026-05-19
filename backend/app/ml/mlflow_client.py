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
    
    def __init__(self, tracking_uri: Optional[str] = None):
        """
        Initialize MLflow client.
        
        Args:
            tracking_uri: MLflow tracking URI
        """
        self.tracking_uri = tracking_uri or settings.MLFLOW_TRACKING_URI
        mlflow.set_tracking_uri(self.tracking_uri)
        self.experiment_name = settings.default_experiment_name
        
    def get_or_create_experiment(self, experiment_name: str = None) -> str:
        """
        Get or create an experiment.
        
        Args:
            experiment_name: Experiment name
            
        Returns:
            Experiment ID
        """
        experiment_name = experiment_name or self.experiment_name
        
        try:
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if experiment is None:
                experiment_id = mlflow.create_experiment(experiment_name)
                logger.info(f"Created new experiment: {experiment_name} (ID: {experiment_id})")
            else:
                experiment_id = experiment.experiment_id
                logger.info(f"Using existing experiment: {experiment_name} (ID: {experiment_id})")
            
            return experiment_id
            
        except Exception as e:
            logger.error(f"Error getting/creating experiment: {str(e)}")
            raise
    
    def start_run(self, run_name: str = None, experiment_name: str = None) -> mlflow.ActiveRun:
        """
        Start an MLflow run.
        
        Args:
            run_name: Run name
            experiment_name: Experiment name
            
        Returns:
            Active run context
        """
        experiment_id = self.get_or_create_experiment(experiment_name)
        
        try:
            run = mlflow.start_run(
                experiment_id=experiment_id,
                run_name=run_name,
                tags={
                    "project": "nexus",
                    "created_at": datetime.now().isoformat()
                }
            )
            
            logger.info(f"Started MLflow run: {run.info.run_name} (ID: {run.info.run_id})")
            return run
            
        except Exception as e:
            logger.error(f"Error starting MLflow run: {str(e)}")
            raise
    
    def log_document_processing(self, filename: str, file_size: int, chunks_processed: int):
        """
        Log document processing metrics.
        
        Args:
            filename: Document filename
            file_size: File size in bytes
            chunks_processed: Number of chunks processed
        """
        with self.start_run(f"document_processing_{filename.replace('.', '_')}") as run:
            mlflow.log_param("filename", filename)
            mlflow.log_param("file_size", file_size)
            mlflow.log_metric("chunks_processed", chunks_processed)
            mlflow.log_metric("processing_efficiency", chunks_processed / (file_size / 1024))  # chunks per KB
            
    def log_query_metrics(self, query: str, response_time: float, confidence: float, 
                         sources_count: int, error: bool = False):
        """
        Log query metrics.
        
        Args:
            query: User query
            response_time: Response time in seconds
            confidence: Confidence score
            sources_count: Number of sources used
            error: Whether the query resulted in an error
        """
        with self.start_run(f"query_{hash(query)}") as run:
            mlflow.log_param("query_length", len(query))
            mlflow.log_param("query_words", len(query.split()))
            mlflow.log_metric("response_time", response_time)
            mlflow.log_metric("confidence", confidence)
            mlflow.log_metric("sources_count", sources_count)
            mlflow.log_metric("error", int(error))
            
            # Log query category based on keywords
            query_categories = ["factual", "comparison", "procedural", "explanatory"]
            mlflow.log_param("query_category", self._categorize_query(query))
    
    def log_evaluation_metrics(self, evaluation_name: str, metrics: Dict[str, float]):
        """
        Log evaluation metrics.
        
        Args:
            evaluation_name: Evaluation name
            metrics: Dictionary of metrics
        """
        with self.start_run(f"evaluation_{evaluation_name}") as run:
            for key, value in metrics.items():
                mlflow.log_metric(key, value)
    
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
        """
        Log embedding generation metrics.
        
        Args:
            text_length: Length of input text
            embedding_time: Time taken to generate embedding
            embedding_dimension: Dimension of embedding vector
        """
        with self.start_run("embedding_generation") as run:
            mlflow.log_param("text_length", text_length)
            mlflow.log_metric("embedding_time", embedding_time)
            mlflow.log_param("embedding_dimension", embedding_dimension)
            mlflow.log_metric("tokens_per_second", text_length / embedding_time)
    
    def log_system_metrics(self, total_queries: int, average_response_time: float,
                          error_rate: float, active_documents: int):
        """
        Log system-wide metrics.
        
        Args:
            total_queries: Total number of queries
            average_response_time: Average response time
            error_rate: Error rate
            active_documents: Number of active documents
        """
        with self.start_run("system_metrics") as run:
            mlflow.log_metric("total_queries", total_queries)
            mlflow.log_metric("average_response_time", average_response_time)
            mlflow.log_metric("error_rate", error_rate)
            mlflow.log_metric("active_documents", active_documents)
    
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
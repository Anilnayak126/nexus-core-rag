import mlflow
import logging
from typing import Optional
import socket
from urllib.parse import urlparse
from datetime import datetime
from app.core.config import settings

logger = logging.getLogger(__name__)

class MLflowClient:

    def __init__(self, tracking_uri: Optional[str] = None, experiment_name: str = "nexus_knowledge_engine"):
        self.tracking_uri = tracking_uri or settings.MLFLOW_TRACKING_URI
        self._connected = self._check_connection()
        if self._connected:
            mlflow.set_tracking_uri(self.tracking_uri)
        else:
            logger.warning("MLflow not available at %s — telemetry disabled", self.tracking_uri)
        self.experiment_name = experiment_name

    @staticmethod
    def _check_connection() -> bool:
        try:
            parsed = urlparse(settings.MLFLOW_TRACKING_URI)
            host = parsed.hostname or "localhost"
            port = parsed.port or 5001
            sock = socket.create_connection((host, port), timeout=1)
            sock.close()
            return True
        except Exception:
            return False

    def _safe_call(self, fn, *args, **kwargs):
        if not self._connected:
            return
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            logger.debug("MLflow call skipped: %s", e)

    def get_or_create_experiment(self, experiment_name: str = None) -> Optional[str]:
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

    def _categorize_query(self, query: str) -> str:
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

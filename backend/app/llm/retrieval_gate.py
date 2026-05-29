"""
Retrieval Gate — blocks hallucinations when no relevant context is found.

Acts as a safety layer between vector search and answer generation.
If retrieved chunks fall below the confidence threshold, the gate
returns a structured "no-context" response instead of letting the
LLM hallucinate.
"""

import time
import logging
from typing import List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class GateDecision:
    passed: bool
    confidence: float
    threshold: float
    chunks_found: int
    reason: str
    timestamp: float = field(default_factory=time.time)


class RetrievalGate:
    def __init__(self, min_confidence: float = 0.5):
        self.min_confidence = min_confidence
        self.total_calls = 0
        self.blocked_calls = 0

    def evaluate(self, chunks: List, confidence: float) -> GateDecision:
        self.total_calls += 1

        if not chunks:
            self.blocked_calls += 1
            logger.warning("Retrieval Gate BLOCKED: no chunks retrieved at all")
            return GateDecision(
                passed=False,
                confidence=0.0,
                threshold=self.min_confidence,
                chunks_found=0,
                reason="No relevant context found in the knowledge base.",
            )

        if confidence < self.min_confidence:
            self.blocked_calls += 1
            logger.warning(
                "Retrieval Gate BLOCKED: confidence %.3f below threshold %.3f",
                confidence,
                self.min_confidence,
            )
            return GateDecision(
                passed=False,
                confidence=confidence,
                threshold=self.min_confidence,
                chunks_found=len(chunks),
                reason=(
                    f"Retrieved context confidence ({confidence:.3f}) is too low "
                    f"to generate a reliable answer."
                ),
            )

        logger.info("Retrieval Gate PASSED: confidence %.3f", confidence)
        return GateDecision(
            passed=True,
            confidence=confidence,
            threshold=self.min_confidence,
            chunks_found=len(chunks),
            reason="Context confidence meets the required threshold.",
        )

    def get_stats(self) -> dict:
        return {
            "total_calls": self.total_calls,
            "blocked_calls": self.blocked_calls,
            "block_rate": self.blocked_calls / max(self.total_calls, 1),
        }

"""Tests for the query endpoint, caching, and retrieval gate."""

import os
import pytest
import httpx

API_URL = os.environ.get("NEXUS_API_URL", "http://localhost:8002")


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=API_URL, timeout=30) as c:
        yield c


class TestQuery:
    def test_query_relevant_returns_sources(self, client):
        resp = client.post(
            "/query",
            json={"question": "What is the Nexus Knowledge Engine?", "top_k": 3},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["confidence"] > 0
        assert len(data["sources"]) >= 1
        assert data["sources"][0]["filename"] == "test_document.pdf"

    def test_query_irrelevant_is_blocked(self, client):
        resp = client.post(
            "/query",
            json={"question": "What is the weather in Tokyo?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["confidence"] == 0.0
        assert len(data["sources"]) == 0
        assert "No relevant context" in data["answer"]

    def test_empty_query_returns_400(self, client):
        resp = client.post(
            "/query",
            json={"question": ""},
        )
        assert resp.status_code == 422


class TestMetrics:
    def test_metrics_endpoint(self, client):
        resp = client.get("/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_queries" in data
        assert "average_response_time" in data
        assert "retrieval_gate" in data
        assert "blocked_calls" in data["retrieval_gate"]

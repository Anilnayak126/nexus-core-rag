"""Tests for the health and document upload endpoints."""

import json
import os
import pytest
import httpx

API_URL = os.environ.get("NEXUS_API_URL", "http://localhost:8002")
TEST_PDF = os.path.join(os.path.dirname(__file__), "test_document.pdf")


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=API_URL, timeout=30) as c:
        yield c


class TestHealth:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "healthy"}


class TestDocumentUpload:
    def test_upload_rejects_non_pdf(self, client):
        resp = client.post(
            "/documents/upload",
            files={"file": ("test.txt", b"not a pdf", "text/plain")},
        )
        assert resp.status_code == 400

    def test_upload_pdf_succeeds(self, client):
        if not os.path.exists(TEST_PDF):
            pytest.skip("test_document.pdf not found")
        with open(TEST_PDF, "rb") as f:
            resp = client.post("/documents/upload", files={"file": f})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["chunks_processed"] >= 1
        assert "document_id" in data

    def test_upload_same_pdf_is_idempotent(self, client):
        if not os.path.exists(TEST_PDF):
            pytest.skip("test_document.pdf not found")
        with open(TEST_PDF, "rb") as f:
            resp1 = client.post("/documents/upload", files={"file": f})
        assert resp1.status_code == 200
        doc_id_1 = resp1.json()["document_id"]

        with open(TEST_PDF, "rb") as f:
            resp2 = client.post("/documents/upload", files={"file": f})
        assert resp2.status_code == 200
        doc_id_2 = resp2.json()["document_id"]

        assert doc_id_1 == doc_id_2, "Re-upload should reuse same document_id"

#!/usr/bin/env python3
"""Generate a minimal test PDF for endpoint testing."""

import zlib


def _escape(val: str) -> str:
    return val.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _stream(data: str) -> bytes:
    return zlib.compress(data.encode("latin-1"))


def main() -> None:
    content = """
The Nexus Knowledge Engine is a RAG system for enterprise knowledge retrieval.

Key Features:
- Document processing with PDF text extraction and sliding window chunking
- Vector embeddings using sentence-transformers (384 dimensions)
- Cosine similarity search via pgvector HNSW index
- Redis semantic caching for duplicate queries
- Retrieval Gate to block low-confidence responses
- MLflow telemetry for query latency and confidence tracking

Architecture:
FastAPI with asyncpg, PostgreSQL/pgvector, Redis, and MLflow.
Documents are uploaded, extracted via PyMuPDF, chunked with overlap,
embedded, and stored in pgvector for efficient vector search.
""".strip()

    raw = f"""BT
/F1 12 Tf
50 750 Td
({_escape(content[:80])}) Tj
0 -15 Td
({_escape(content[80:160])}) Tj
0 -15 Td
({_escape(content[160:240])}) Tj
0 -15 Td
({_escape(content[240:320])}) Tj
0 -15 Td
({_escape(content[320:400])}) Tj
0 -15 Td
({_escape(content[400:480])}) Tj
0 -15 Td
({_escape(content[480:])}) Tj
ET"""

    compressed = _stream(raw)

    objs = []
    objs.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objs.append(
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    )
    objs.append(
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 5 0 R /Resources << /Font << /F1 4 0 R >> >> >>\nendobj\n"
    )
    objs.append(
        b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    )
    objs.append(
        b"5 0 obj\n<< /Length " + str(len(compressed)).encode()
        + b" /Filter /FlateDecode >>\nstream\n" + compressed + b"\nendstream\nendobj\n"
    )

    xref_offset = None
    body = b""
    for i, o in enumerate(objs):
        body += o

    offset_bytes = b""
    offsets = []
    offset_bytes += b"%PDF-1.4\n"
    for o in objs:
        offsets.append(len(offset_bytes))
        offset_bytes += o
    xref_offset = len(offset_bytes)
    offset_bytes += b"xref\n"
    offset_bytes += f"0 {len(objs) + 1}\n".encode()
    offset_bytes += b"0000000000 65535 f \n"
    for off in offsets:
        offset_bytes += f"{off:010d} 00000 n \n".encode()
    offset_bytes += b"trailer\n<< /Size " + str(len(objs) + 1).encode()
    offset_bytes += b" /Root 1 0 R >>\n"
    offset_bytes += b"startxref\n" + str(xref_offset).encode() + b"\n%%EOF\n"

    out_path = "backend/tests/test_document.pdf"
    with open(out_path, "wb") as f:
        f.write(offset_bytes)

    print(f"Created {out_path} ({len(offset_bytes)} bytes)")


if __name__ == "__main__":
    main()

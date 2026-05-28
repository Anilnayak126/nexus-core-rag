# Testing Guide — Phase 1 & Phase 2

This guide walks through how to verify every feature from Phase 1 (Core Backend) and Phase 2 (LLMOps & Production Safety) is working correctly.

## Prerequisites

```bash
# Start the full stack
make dev-up
```

Verify all containers are running:

```bash
docker ps --filter "name=nexus-*" --format "table {{.Names}}\t{{.Status}}"
```

Expected output:

| Name | Status |
|---|---|
| nexus-api | Up |
| nexus-vector-db | Up |
| nexus-redis | Up |
| nexus-pgadmin | Up |

---

## Phase 1 Tests (Days 1-7)

### 1. Health Check

```bash
curl -s http://localhost:8002/health
```

**Expected:** `{"status":"healthy"}`

---

### 2. Document Upload (Day 3-4)

Create a test PDF:

```bash
cat > /tmp/test-doc.md << 'EOF'
# Nexus Knowledge Engine

The Nexus Knowledge Engine is a RAG system for enterprise knowledge retrieval.

## Features

- Document ingestion with PDF text extraction
- Sliding Window chunking with configurable overlap
- Vector embeddings using sentence-transformers
- Cosine similarity search via pgvector HNSW index
- Redis caching for duplicate queries
- MLflow tracking for telemetry

## Architecture

The system uses FastAPI as the web framework, PostgreSQL with pgvector for vector storage,
Redis for caching, and MLflow for experiment tracking.
EOF

# Convert to PDF (requires pandoc)
pandoc /tmp/test-doc.md -o /tmp/test-doc.pdf
# OR create a minimal PDF with Python
python3 -c "
from fpdf import FPDF
pdf = FPDF()
pdf.add_page()
pdf.set_font('Arial', size=12)
with open('/tmp/test-doc.md') as f:
    for line in f:
        pdf.cell(200, 10, txt=line.strip(), ln=True)
pdf.output('/tmp/test-doc.pdf')
"
```

Upload the PDF:

```bash
curl -s -X POST http://localhost:8002/documents/upload \
  -F "file=@/tmp/test-doc.pdf" | python3 -m json.tool
```

**Expected output:**
```json
{
    "message": "Document processed successfully",
    "document_id": 1,
    "filename": "test-doc.pdf",
    "chunks_processed": 2,
    "status": "success"
}
```

**What verifies:**
- PDF text extraction via PyMuPDF ✅
- Sliding Window chunking (chunk_size=1000, overlap=200) ✅
- Embedding generation via sentence-transformers ✅
- Storage in pgvector `document_chunks` table ✅
- HNSW index creation ✅

---

### 3. Query Knowledge Base (Day 5-7)

```bash
curl -s -X POST http://localhost:8002/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the Nexus Knowledge Engine?", "top_k": 3}' | python3 -m json.tool
```

**Expected output:**
```json
{
    "answer": "Based on the provided context...",
    "sources": [
        {
            "content": "...",
            "filename": "test-doc.pdf",
            "similarity": 0.85,
            "chunk_index": 0
        }
    ],
    "confidence": 0.85,
    "processing_time": 0.5
}
```

**What verifies:**
- Query embedding generation ✅
- pgvector cosine similarity search via HNSW ✅
- LangChain PromptTemplate formatting ✅
- Response with sources + confidence ✅

---

### 4. Semantic Caching (Day 8-9 — also Phase 2)

Run the **same query** again:

```bash
curl -s -X POST http://localhost:8002/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the Nexus Knowledge Engine?", "top_k": 3}' | python3 -m json.tool
```

**Expected:** `processing_time` is ~0.0s (near-instant from cache)

Run a **semantically similar query** (differently worded):

```bash
curl -s -X POST http://localhost:8002/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Tell me about the Nexus Knowledge Engine", "top_k": 3}' | python3 -m json.tool
```

**Expected:** Fast response (semantic cache hit, cosine >= 0.95)

Check Redis cache entries:

```bash
docker exec nexus-redis redis-cli KEYS "search:*" | wc -l
docker exec nexus-redis redis-cli KEYS "semantic_cache:*" | wc -l
```

**Expected:** Both commands return > 0 cache entries.

**What verifies:**
- Exact hash cache works ✅
- Semantic (embedding-based) cache works ✅
- Differently-worded queries hit semantic cache ✅

---

## Phase 2 Tests (Days 8-14)

### 5. Retrieval Gate (Day 10-11)

Query with no relevant context (should be blocked):

```bash
curl -s -X POST http://localhost:8002/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the weather in Tokyo?", "top_k": 3}' | python3 -m json.tool
```

**Expected output:**
```json
{
    "answer": "No relevant context found in the knowledge base.",
    "sources": [],
    "confidence": 0.0,
    "processing_time": 0.1
}
```

Query with low-confidence context:

```bash
curl -s -X POST http://localhost:8002/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Tokyo weather forecast 2025", "top_k": 3}' | python3 -m json.tool
```

**Expected:** Answer says confidence is too low to generate a reliable answer.

Check gate statistics:

```bash
curl -s http://localhost:8002/metrics | python3 -m json.tool
```

**Expected output:**
```json
{
    "total_queries": 4,
    "average_response_time": 0.3,
    "error_rate": 0.5,
    "average_confidence": 0.4,
    "retrieval_gate": {
        "total_calls": 2,
        "blocked_calls": 2,
        "block_rate": 1.0
    }
}
```

**What verifies:**
- Retrieval Gate blocks queries with no context ✅
- Retrieval Gate blocks queries with confidence < 0.5 ✅
- Gate stats exposed via `/metrics` ✅
- Block rate calculation ✅

---

### 6. MLflow Telemetry (Day 12-14)

Verify MLflow is running:

```bash
curl -s http://localhost:5001/api/2.0/mlflow/experiments/list | python3 -m json.tool
```

**Expected:** Response with experiment list.

Check MLflow runs were created:

```bash
# Number of runs created by queries
curl -s "http://localhost:5001/api/2.0/mlflow/runs/search?experiment_ids=[0]" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Total runs: {len(data.get(\"runs\", []))}')
for run in data.get('runs', [])[:3]:
    name = run['data']['params'][0]['value'] if run['data']['params'] else 'no params'
    print(f'  - {run[\"info\"][\"run_name\"]}')
"
```

**Expected:** Shows query metrics runs and retrieval gate blocked runs.

Check retrieval gate events in MLflow:

```bash
# Check for retrieval_gate_blocked runs
curl -s "http://localhost:5001/api/2.0/mlflow/runs/search?experiment_ids=[0]" | python3 -c "
import sys, json
data = json.load(sys.stdin)
gate_runs = [r for r in data.get('runs', []) if 'gate' in r['info']['run_name'].lower()]
print(f'Retrieval gate events logged: {len(gate_runs)}')
"
```

**Expected:** Shows retrieval gate block events were logged.

**What verifies:**
- MLflow client initializes on startup ✅
- Query metrics logged (latency, confidence, sources_count) ✅
- Retrieval gate events logged separately in MLflow ✅
- Error tracking for blocked queries ✅

---

### 7. Seed Data Verification

Verify demo data exists in the database:

```bash
docker exec nexus-vector-db psql -U admin -d nexus_knowledge -c "SELECT id, filename FROM documents;"
```

**Expected:** Shows demo documents from seed data (getting-started.md, api-reference.pdf, etc.)

```bash
docker exec nexus-vector-db psql -U admin -d nexus_knowledge -c "SELECT COUNT(*) as total_chunks FROM document_chunks;"
```

**Expected:** Shows total chunk count.

---

## End-to-End Test Script

Save this as `test_e2e.sh` and run it for a single-command verification:

```bash
#!/usr/bin/env bash
set -e

BASE="http://localhost:8002"
PASS=0
FAIL=0

check() {
    local desc="$1"
    local actual="$2"
    local expected="$3"
    if echo "$actual" | grep -q "$expected"; then
        echo "  ✅ $desc"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $desc (expected: $expected)"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== Nexus E2E Tests ==="

echo "1. Health check"
check "Health endpoint" "$(curl -s $BASE/health)" "healthy"

echo "2. Document upload"
python3 -c "
from fpdf import FPDF
pdf = FPDF(); pdf.add_page(); pdf.set_font('Arial', size=12)
pdf.cell(200, 10, txt='Nexus RAG system test document', ln=True)
pdf.output('/tmp/e2e-test.pdf')
"
RESP=$(curl -s -X POST $BASE/documents/upload -F "file=@/tmp/e2e-test.pdf")
check "Upload success" "$RESP" "success"
check "Has document_id" "$RESP" "document_id"

echo "3. Query with context"
RESP=$(curl -s -X POST $BASE/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Nexus RAG system"}')
check "Query returns answer" "$RESP" "answer"
check "Has sources" "$RESP" "sources"

echo "4. Retrieval Gate (no context)"
RESP=$(curl -s -X POST $BASE/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Tokyo weather"}')
check "Gate blocks no-context" "$RESP" "No relevant context"

echo "5. Metrics"
RESP=$(curl -s $BASE/metrics)
check "Metrics endpoint" "$RESP" "retrieval_gate"
check "Has total_queries" "$RESP" "total_queries"

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
exit $FAIL
```

---

## Quick Reference

| Test | Command | Expected |
|---|---|---|
| Health | `curl localhost:8002/health` | `{"status":"healthy"}` |
| Upload | `curl -X POST .../upload -F "file=@doc.pdf"` | `"status":"success"` |
| Query | `curl -X POST .../query -d '{"question":"..."}'` | Answer with sources |
| No context | `curl .../query -d '{"question":"unknown topic"}'` | Gate blocks it |
| Metrics | `curl localhost:8002/metrics` | Query + gate stats |
| MLflow | `curl localhost:5001/api/2.0/mlflow/experiments/list` | Experiment list |
| Redis cache | `docker exec nexus-redis redis-cli KEYS "search:*"` | Cache entries exist |
| DB verify | `docker exec nexus-vector-db psql ... -c "SELECT ..."` | Documents + chunks |

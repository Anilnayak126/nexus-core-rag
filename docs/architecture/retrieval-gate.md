# Retrieval Gate

```mermaid
flowchart TB
    Chunks[Retrieved Chunks]
    Conf[Calculate Confidence]

    Conf -->|Conf >= 0.5 & chunks exist| Pass[Gate Passed]
    Conf -->|Conf < 0.5| Block[Gate Blocked]
    Conf -->|No chunks| Block

    Pass -->|Format answer with sources| Response
    Block -->|"No relevant context found"| Response

    Response --> Metrics
    Metrics[/metrics endpoint]

    subgraph Stats["Gate Statistics"]
        Total[total_calls++]
        Blocked[blocked_calls++ on block]
        Rate[block_rate = blocked / total]
    end

    Pass --> Total
    Block --> Total
    Block --> Blocked
    Total --> Rate

    style Block fill:#FF6B6B,color:#fff
    style Pass fill:#50C878,color:#fff
    style Rate fill:#4A90D9,color:#fff
```

## Configuration

| Parameter | Value | Description |
|-----------|-------|-------------|
| `min_confidence` | 0.5 | Minimum confidence to allow answer |
| `similarity_threshold` | 0.6 | Minimum cosine similarity for chunk inclusion |

## /metrics Response

```json
{
  "total_queries": 10,
  "average_response_time": 0.023,
  "error_rate": 0.3,
  "average_confidence": 0.45,
  "retrieval_gate": {
    "total_calls": 10,
    "blocked_calls": 3,
    "block_rate": 0.3
  }
}
```

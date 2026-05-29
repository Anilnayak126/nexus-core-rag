# Retrieval Gate

```mermaid
flowchart TB
    Chunks[Retrieved Chunks]
    Conf[Calculate Confidence]

    Conf -->|Conf gte 0.5| Pass[Gate Passed]
    Conf -->|Conf lt 0.5| Block[Gate Blocked]
    Conf -->|No chunks| Block

    Pass -->|Format answer| Response
    Block -->|Return blocked msg| Response

    Response --> Metrics
    Metrics[[/metrics]]

    subgraph GateStats[Gate Statistics]
        TotalCalls[total_calls++]
        BlockedCalls[blocked_calls++]
        CalcRate[block_rate]
    end

    Pass --> TotalCalls
    Block --> TotalCalls
    Block --> BlockedCalls
    BlockedCalls --> CalcRate
    TotalCalls --> CalcRate

    style Block fill:#FF6B6B,color:#fff
    style Pass fill:#50C878,color:#fff
    style Metrics fill:#4A90D9,color:#fff
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

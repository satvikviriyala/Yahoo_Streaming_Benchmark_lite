# comparative_analysis.md

## 1. Executive Summary
[Summarize the key findings. Which engine performed better? What were the trade-offs?]

## 2. Watermarking Strategies

### Apache Spark
- **Strategy**: [Describe strategy used, e.g., Fixed delay]
- **Configuration**: `withWatermark("event_time", "5 seconds")`
- **Observations**: [How did it handle late data? Did it drop data?]

### Apache Flink
- **Strategy**: [Describe strategy used, e.g., BoundedOutOfOrderness]
- **Configuration**: `Duration.ofSeconds(5)` with `withIdleness`
- **Observations**: [How did it handle idle partitions?]

## 3. Parallelism Impact

| Parallelism | Spark Throughput (events/sec) | Flink Throughput (events/sec) |
| :--- | :--- | :--- |
| 1 | | |
| 2 | | |
| 4 | | |
| 8 | | |

**Analysis**:
[Discuss how scaling parallelism affected throughput and latency for each engine.]

## 4. Performance Under Stress

### SPP (Steady State)
- **Max Sustainable Throughput (Spark)**: [Value]
- **Max Sustainable Throughput (Flink)**: [Value]

### MMPP (Variable Load)
- **Spark Behavior**: [Describe latency spikes, backpressure]
- **Flink Behavior**: [Describe latency stability, backpressure]

## 5. Architectural Differences
- **Spark**: Micro-batch architecture. [Pros/Cons observed]
- **Flink**: Continuous streaming. [Pros/Cons observed]

## 6. Recommendations
[When to use Spark vs Flink based on this assignment?]

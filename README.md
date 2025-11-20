# Assignment 4: Stream Processing Engine Replacement

This project implements a Click-Through Rate (CTR) calculation pipeline using **Apache Spark Structured Streaming** and **Apache Flink**, replacing the previous SQL-based implementation. It includes data generators (SPP, MMPP) and analysis scripts for benchmarking.

## Project Structure

- `spark/`: Spark Structured Streaming implementation (Python).
- `flink/`: Flink DataStream API implementation (Java).
- `generators/`: Data generators for Steady Poisson Process (SPP) and Markov-Modulated Poisson Process (MMPP).
- `analysis/`: Scripts for calculating end-to-end latency and analyzing results.
- `docker-compose.yml`: Kafka and Zookeeper infrastructure.

## Prerequisites

- Docker & Docker Compose
- Python 3.8+
- Java 8 or 11 (for Flink)
- Maven (for building Flink job)

## Setup

1. **Start Infrastructure**:
   ```bash
   docker-compose up -d
   ```

2. **Install Python Dependencies**:
   ```bash
   pip install -r spark/requirements.txt
   ```

3. **Build Flink Job**:
   ```bash
   cd flink
   mvn clean package
   cd ..
   ```

## Running the Pipeline

### 1. Start Data Generator
Choose one of the generators:

- **Steady Poisson Process (SPP)** (Baseline):
  ```bash
  python generators/spp_generator.py --rate 100
  ```

- **Markov-Modulated Poisson Process (MMPP)** (Stress Test):
  ```bash
  python generators/mmpp_generator.py --low-rate 100 --high-rate 1000 --switch-interval 60
  ```

### 2. Run Stream Processing Engine

#### Option A: Apache Spark
```bash
python spark/src/main.py
```
Output Topic: `ysb-ctr-results-spark`

#### Option B: Apache Flink
```bash
flink run -c org.example.YSBCTRJob flink/target/flink-ysb-ctr-1.0-SNAPSHOT.jar
```
*(Note: Ensure you have Flink installed locally or submit to a Flink cluster. Alternatively, run from IDE)*
Output Topic: `ysb-ctr-results-flink`

### 3. Analyze Results
Run the latency analyzer to monitor end-to-end latency:

```bash
# For Spark
python analysis/latency_analyzer.py --topic ysb-ctr-results-spark

# For Flink
python analysis/latency_analyzer.py --topic ysb-ctr-results-flink
```

## Benchmarking Strategy

1. **Baseline (SPP)**: Run both engines with a steady rate (e.g., 1000 events/sec) and measure average latency.
2. **Max Throughput**: Increase the rate until latency exceeds 1 second.
3. **Stress Test (MMPP)**: Run with alternating load to observe backpressure handling and watermark progression.

## Configuration

- **Spark**: `spark/src/config.py`
- **Flink**: `flink/src/main/java/org/example/config/JobConfig.java`

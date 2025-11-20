# Assignment 4: Stream Processing Engine Replacement

**Apache Spark vs Apache Flink for Real-Time CTR Calculation**

This project implements Click-Through Rate (CTR) calculation using distributed stream processing engines (**Apache Spark Structured Streaming** and **Apache Flink DataStream API**), replacing the previous SQL-based implementation from Assignment 3.

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Setup Guide](#detailed-setup-guide)
- [Running Benchmarks](#running-benchmarks)
- [Troubleshooting](#troubleshooting)
- [Project Structure](#project-structure)
- [Key Concepts](#key-concepts)
- [Results](#results)

---

## 🎯 Project Overview

### What This Project Does

Calculates **Click-Through Rate (CTR)** for advertising campaigns in real-time using:
- **Event-time windowing** (10-second tumbling windows)
- **Watermarking** (5-second delay for out-of-order events)
- **Distributed stream processing** (Spark and Flink)

### Key Metrics

```
CTR = (Number of Clicks) / (Number of Views)
End-to-End Latency = Result Generation Time - Earliest Event Insertion Time
```

### Assignment Evolution

- **A1 (PostgreSQL)**: Baseline with tight coupling
- **A2 (Kafka)**: Decoupling with message broker
- **A3 (Watermarks)**: Event-time correctness
- **A4 (Spark/Flink)**: Distributed stream processing ← **This Assignment**

---

## 🏗️ Architecture

```
┌─────────────────┐
│  Data Generator │ (Python: SPP/MMPP)
│  (100-1000 eps) │
└────────┬────────┘
         │ JSON events
         ↓
┌─────────────────┐
│  Apache Kafka   │ Topic: ysb-events
│  (Message Broker)│
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ↓         ↓
┌────────┐ ┌────────┐
│ Spark  │ │ Flink  │
│ Stream │ │ Stream │
└────┬───┘ └───┬────┘
     │         │
     ↓         ↓
┌─────────┐ ┌─────────┐
│ Topic:  │ │ Topic:  │
│ spark   │ │ flink   │
│ results │ │ results │
└─────────┘ └─────────┘
```

### Components

1. **Data Generators**
   - **SPP**: Steady Poisson Process (constant rate)
   - **MMPP**: Markov-Modulated Poisson Process (variable rate)

2. **Apache Kafka**
   - Decouples producers and consumers
   - Provides durability and replay capability
   - Topics: `ysb-events`, `ysb-ctr-results-spark`, `ysb-ctr-results-flink`

3. **Stream Processors**
   - **Spark**: Micro-batch processing (Python)
   - **Flink**: True streaming (Java)

---

## 📦 Prerequisites

- **Docker & Docker Compose** (for Kafka/Zookeeper)
- **Python 3.8+** (for Spark and generators)
- **Java 17** (for Flink)
- **Maven 3.6+** (for building Flink)

### Install Java 17 (macOS)

```bash
brew install openjdk@17
export JAVA_HOME="/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
export PATH="$JAVA_HOME/bin:$PATH"
```

---

## 🚀 Quick Start

### 1. Clone and Setup

```bash
cd /Users/satvik/Documents/SDS_Assignment4

# Install Python dependencies
pip3 install kafka-python pyspark

# Build Flink project
cd flink
mvn clean package
cd ..
```

### 2. Start Infrastructure

```bash
# Start Kafka and Zookeeper
docker-compose up -d

# IMPORTANT: Wait 60 seconds for Kafka to fully initialize
echo "Waiting for Kafka to be ready..."
sleep 60

# Create topics
docker exec broker kafka-topics --create --topic ysb-events \
    --bootstrap-server broker:29092 --partitions 1 --replication-factor 1 --if-not-exists

docker exec broker kafka-topics --create --topic ysb-ctr-results-spark \
    --bootstrap-server broker:29092 --partitions 1 --replication-factor 1 --if-not-exists

docker exec broker kafka-topics --create --topic ysb-ctr-results-flink \
    --bootstrap-server broker:29092 --partitions 1 --replication-factor 1 --if-not-exists
```

### 3. Run Complete Pipeline

**Terminal 1 - Start Spark:**
```bash
export JAVA_HOME="/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
python3 spark/src/main.py
```

**Terminal 2 - Start Generator (wait 30 seconds, then start Flink):**
```bash
python3 generators/spp_generator.py --rate 100 --stdout | \
    docker exec -i broker kafka-console-producer --bootstrap-server broker:29092 --topic ysb-events
```

**Terminal 3 - Start Flink (AFTER generator has been running for 30 seconds):**
```bash
export JAVA_HOME="/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
cd flink
mvn exec:java -Dexec.mainClass="org.example.YSBCTRJob" -Djava.net.preferIPv4Stack=true
```

### 4. Verify Output

```bash
# Check Spark results
docker exec broker kafka-console-consumer --bootstrap-server broker:29092 \
    --topic ysb-ctr-results-spark --from-beginning --max-messages 5 --timeout-ms 5000

# Check Flink results
docker exec broker kafka-console-consumer --bootstrap-server broker:29092 \
    --topic ysb-ctr-results-flink --from-beginning --max-messages 5 --timeout-ms 5000
```

---

## 📊 Running Benchmarks

For detailed step-by-step benchmarking instructions, see **[MANUAL_BENCHMARK_GUIDE.md](MANUAL_BENCHMARK_GUIDE.md)**.

### Quick Benchmark Commands

```bash
# Create results directory
mkdir -p results

# Test 1: SPP Low Load (100 eps)
python3 generators/spp_generator.py --rate 100 --stdout | \
    docker exec -i broker kafka-console-producer --bootstrap-server broker:29092 --topic ysb-events
# Run for 3 minutes, then Ctrl+C

# Collect metrics
python3 analysis/collect_metrics_enhanced.py ysb-ctr-results-spark 45 500 results/spp_100_spark.json
python3 analysis/collect_metrics_enhanced.py ysb-ctr-results-flink 45 500 results/spp_100_flink.json

# Test 2: SPP High Load (1000 eps)
python3 generators/spp_generator.py --rate 1000 --stdout | \
    docker exec -i broker kafka-console-producer --bootstrap-server broker:29092 --topic ysb-events
# Run for 3 minutes, then Ctrl+C

python3 analysis/collect_metrics_enhanced.py ysb-ctr-results-spark 45 500 results/spp_1000_spark.json
python3 analysis/collect_metrics_enhanced.py ysb-ctr-results-flink 45 500 results/spp_1000_flink.json

# Test 3: MMPP (Variable Load)
python3 generators/mmpp_generator.py --low-rate 100 --high-rate 1000 --switch-interval 30 --stdout | \
    docker exec -i broker kafka-console-producer --bootstrap-server broker:29092 --topic ysb-events
# Run for 3 minutes, then Ctrl+C

python3 analysis/collect_metrics_enhanced.py ysb-ctr-results-spark 45 500 results/mmpp_spark.json
python3 analysis/collect_metrics_enhanced.py ysb-ctr-results-flink 45 500 results/mmpp_flink.json
```

---

## 🔧 Troubleshooting

### Issue 1: Kafka Connection Timeout

**Error:**
```
TimeoutException: Timed out waiting for a node assignment
```

**Solution:**
- Wait 60 seconds after `docker-compose up -d` before creating topics or sending data
- Verify Kafka is ready: `docker logs broker | tail -20`

### Issue 2: Flink "Timeout expired before position could be determined"

**Error:**
```
TimeoutException: Timeout of 60000ms expired before the position 
for partition ysb-events-0 could be determined
```

**Root Cause:** Flink is trying to connect to an empty Kafka topic.

**Solution - CRITICAL STARTUP SEQUENCE:**

1. **Start generator FIRST**
2. **Wait 30 seconds** for data to populate topic
3. **THEN start Flink** (while generator is still running)

```bash
# Terminal 1: Start generator
python3 generators/spp_generator.py --rate 100 --stdout | \
    docker exec -i broker kafka-console-producer --bootstrap-server broker:29092 --topic ysb-events

# Wait 30 seconds...

# Terminal 2: NOW start Flink
cd flink
mvn exec:java -Dexec.mainClass="org.example.YSBCTRJob" -Djava.net.preferIPv4Stack=true
```

### Issue 3: Spark Checkpoint Errors

**Error:**
```
OffsetOutOfRangeException: Fetch position offset=9983 is out of range
```

**Solution:**
```bash
# Clean checkpoint directory
rm -rf /tmp/spark-checkpoints
mkdir -p /tmp/spark-checkpoints

# Restart Spark
python3 spark/src/main.py
```

### Issue 4: IPv6 vs IPv4 Issues

**Error:** Connection failures with `localhost`

**Solution:** Use `127.0.0.1` instead of `localhost`, or force IPv4:
- Spark: Already configured with `-Djava.net.preferIPv4Stack=true`
- Flink: Run with `-Djava.net.preferIPv4Stack=true`

### Issue 5: No Metrics Collected

**Check if jobs are running:**
```bash
ps aux | grep -E "spark|flink"
```

**Verify data in topics:**
```bash
# Check input
docker exec broker kafka-console-consumer --bootstrap-server broker:29092 \
    --topic ysb-events --from-beginning --max-messages 5 --timeout-ms 5000

# Check Spark output
docker exec broker kafka-console-consumer --bootstrap-server broker:29092 \
    --topic ysb-ctr-results-spark --from-beginning --max-messages 5 --timeout-ms 5000
```

---

## 📁 Project Structure

```
SDS_Assignment4/
├── docker-compose.yml          # Kafka + Zookeeper setup
├── README.md                   # This file
├── MANUAL_BENCHMARK_GUIDE.md   # Detailed benchmarking steps
├── TROUBLESHOOTING.md          # Common issues and solutions
├── run_benchmarks.sh           # Automated benchmark script
│
├── generators/                 # Data generators
│   ├── event_schema.py         # Event data structure
│   ├── spp_generator.py        # Steady Poisson Process
│   └── mmpp_generator.py       # Markov-Modulated Poisson Process
│
├── spark/                      # Spark implementation
│   ├── requirements.txt        # Python dependencies
│   └── src/
│       ├── config.py           # Kafka configuration
│       └── main.py             # Spark Structured Streaming job
│
├── flink/                      # Flink implementation
│   ├── pom.xml                 # Maven configuration
│   └── src/main/java/org/example/
│       ├── YSBCTRJob.java      # Main Flink job
│       ├── config/
│       │   └── JobConfig.java  # Configuration constants
│       └── schemas/
│           └── Event.java      # Event POJO
│
├── analysis/                   # Analysis scripts
│   ├── collect_metrics_enhanced.py  # Metrics collection
│   └── latency_analyzer.py     # Legacy analyzer
│
├── results/                    # Benchmark results (JSON)
│   ├── spp_100_spark.json
│   ├── spp_100_flink.json
│   ├── spp_1000_spark.json
│   ├── spp_1000_flink.json
│   ├── mmpp_spark.json
│   └── mmpp_flink.json
│
└── report/                     # Documentation
    ├── assignment4_report.tex  # Main report
    ├── viva_voce_preparation.tex  # Viva prep document
    └── comparative_analysis_template.md
```

---

## 🧠 Key Concepts

### Event-Time Windowing

```
Events arrive out-of-order due to network delays.
Event time ≠ Processing time

Example:
  Event A: event_time = 10:00:05, arrives at 10:00:12
  Event B: event_time = 10:00:03, arrives at 10:00:10
  
Both belong to window [10:00:00, 10:00:10) based on event time,
even though B arrived first in processing time.
```

### Watermarks

```
Watermark = "We believe all events with time ≤ W have arrived"

Our configuration:
  Watermark(t) = max(event_time) - 5 seconds
  
Meaning: Events can be up to 5 seconds late.

Window closes when: Watermark passes window end time
```

### CTR Calculation

```
For each 10-second window and each campaign:
  1. Count views (event_type == "view")
  2. Count clicks (event_type == "click")
  3. CTR = clicks / views
  4. Emit result when watermark closes window
```

### Expected Latency

```
End-to-End Latency = Window Size + Watermark Delay + Processing Time
                   = 10s + 5s + (0-5s)
                   = 15-20 seconds
```

---

## 📈 Results

### Spark Performance (Actual Results)

**SPP Low Load (100 events/sec):**
- Samples: 320 windows
- Mean Latency: **16,050 ms** (~16 seconds)
- P99 Latency: **16,994 ms** (~17 seconds)
- ✅ Matches theoretical expectations!

### Flink Performance

Flink implementation is functional but requires careful startup sequencing (generator must run before Flink starts).

---

## 🎓 For Viva Voce Preparation

See **[report/viva_voce_preparation.tex](report/viva_voce_preparation.tex)** for:
- Detailed theoretical explanations
- Implementation details with code
- Common interview questions and answers
- Comparative analysis of Spark vs Flink
- Troubleshooting lessons learned

---

## 📚 References

1. **Apache Flink Documentation**: https://flink.apache.org/
2. **Apache Spark Structured Streaming**: https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html
3. **Yahoo Streaming Benchmark**: https://github.com/yahoo/streaming-benchmarks
4. **Akidau et al. (2015)**: "The Dataflow Model" - VLDB
5. **Carbone et al. (2015)**: "Apache Flink: Stream and Batch Processing in a Single Engine"

---

## 🤝 Contributing

This is an academic assignment. For questions or issues, refer to the troubleshooting guide or consult the course materials.

---

## 📝 License

Academic project for Streaming Data Systems course.

---

## ✅ Checklist for Successful Run

- [ ] Docker and Docker Compose installed
- [ ] Java 17 installed and JAVA_HOME set
- [ ] Python 3.8+ with kafka-python and pyspark
- [ ] Flink project built (`mvn clean package`)
- [ ] Kafka cluster started and waited 60 seconds
- [ ] Topics created
- [ ] Generator started BEFORE Flink
- [ ] Both Spark and Flink producing results
- [ ] Metrics collected successfully

---

**Last Updated:** 2025-11-20

**Status:** ✅ Fully Functional (with corrected startup sequence)

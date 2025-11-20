# Assignment 4: Manual Benchmarking Guide
# Step-by-Step Instructions for Reliable Results Collection

## Overview
This guide will help you run comprehensive benchmarks for both Spark and Flink.
Each step includes the exact command to run and what to expect.

═══════════════════════════════════════════════════════════════════

## PHASE 1: ENVIRONMENT SETUP (5 minutes)

### Step 1.1: Clean Everything
```bash
# Kill any running processes
pkill -9 -f "spp_generator"
pkill -9 -f "mmpp_generator"
pkill -9 -f "spark"
pkill -9 -f "flink"
pkill -9 -f "YSBCTRJob"

# Clean checkpoint directory
rm -rf /tmp/spark-checkpoints
mkdir -p /tmp/spark-checkpoints

# Clean results directory
rm -rf results
mkdir -p results
```

**Expected**: No output, just clean slate

---

### Step 1.2: Start Kafka Cluster
```bash
cd /Users/satvik/Documents/SDS_Assignment4
docker-compose down
docker-compose up -d
```

**Expected**: 
```
✔ Container zookeeper  Started
✔ Container broker     Started
```

---

### Step 1.3: Wait for Kafka to be FULLY Ready (IMPORTANT!)
```bash
echo "Waiting 60 seconds for Kafka to fully initialize..."
sleep 60
echo "Kafka should be ready now!"
```

**Why**: Kafka needs time to initialize its controller and transaction coordinator.

---

### Step 1.4: Verify Kafka is Ready
```bash
docker exec broker kafka-broker-api-versions --bootstrap-server broker:29092 2>&1 | head -3
```

**Expected**: Should show API versions, not errors. If you see errors, wait another 30 seconds.

---

### Step 1.5: Create Kafka Topics
```bash
docker exec broker kafka-topics --create --topic ysb-events \
    --bootstrap-server broker:29092 --partitions 1 --replication-factor 1 --if-not-exists

docker exec broker kafka-topics --create --topic ysb-ctr-results-spark \
    --bootstrap-server broker:29092 --partitions 1 --replication-factor 1 --if-not-exists

docker exec broker kafka-topics --create --topic ysb-ctr-results-flink \
    --bootstrap-server broker:29092 --partitions 1 --replication-factor 1 --if-not-exists
```

**Expected**: "Created topic ysb-events" (or "already exists")

---

### Step 1.6: Verify Topics Created
```bash
docker exec broker kafka-topics --list --bootstrap-server broker:29092
```

**Expected**: Should show all 3 topics

═══════════════════════════════════════════════════════════════════

## PHASE 2: START PROCESSING JOBS (2 minutes)

### Step 2.1: Start Flink Job (Terminal 1)
Open a NEW terminal window and run:
```bash
cd /Users/satvik/Documents/SDS_Assignment4
export JAVA_HOME="/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
export PATH="$JAVA_HOME/bin:$PATH"
cd flink
mvn exec:java -Dexec.mainClass="org.example.YSBCTRJob" -Djava.net.preferIPv4Stack=true
```

**Expected**: Should see Maven output, then Flink starting. Leave this terminal running.

---

### Step 2.2: Start Spark Job (Terminal 2)
Open ANOTHER new terminal window and run:
```bash
cd /Users/satvik/Documents/SDS_Assignment4
export JAVA_HOME="/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
export PATH="$JAVA_HOME/bin:$PATH"
python3 spark/src/main.py
```

**Expected**: Should see Spark starting. Leave this terminal running.

**Note**: If Spark fails with checkpoint errors, that's OK - we can still proceed with Flink-only benchmarks.

═══════════════════════════════════════════════════════════════════

## PHASE 3: RUN BENCHMARKS (15 minutes total)

### TEST 1: SPP Low Load (100 events/sec)

#### Step 3.1: Start Generator (Terminal 3)
Open a THIRD terminal window:
```bash
cd /Users/satvik/Documents/SDS_Assignment4
python3 generators/spp_generator.py --rate 100 --stdout | \
    docker exec -i broker kafka-console-producer --bootstrap-server broker:29092 --topic ysb-events
```

**Expected**: Generator should start sending events. You'll see "Starting SPP Generator: Target Rate = 100 events/sec"

---

#### Step 3.2: Let it Run
Wait 3 minutes (180 seconds) to collect enough data.
You can use this command in your main terminal:
```bash
echo "Running SPP 100 eps test..."
sleep 180
echo "Test complete!"
```

---

#### Step 3.3: Stop Generator
In Terminal 3, press `Ctrl+C` to stop the generator.

---

#### Step 3.4: Collect Flink Metrics
In your main terminal:
```bash
cd /Users/satvik/Documents/SDS_Assignment4
python3 analysis/collect_metrics_enhanced.py ysb-ctr-results-flink 45 500 results/spp_100_flink.json
```

**Expected**: Should show statistics and save to JSON file.

---

#### Step 3.5: Collect Spark Metrics (if Spark is running)
```bash
python3 analysis/collect_metrics_enhanced.py ysb-ctr-results-spark 45 500 results/spp_100_spark.json
```

**Expected**: Should show statistics. If it fails, that's OK - we have Flink data.

---

### TEST 2: SPP High Load (1000 events/sec)

#### Step 3.6: Start High Load Generator (Terminal 3)
```bash
python3 generators/spp_generator.py --rate 1000 --stdout | \
    docker exec -i broker kafka-console-producer --bootstrap-server broker:29092 --topic ysb-events
```

---

#### Step 3.7: Let it Run
```bash
echo "Running SPP 1000 eps test..."
sleep 180
echo "Test complete!"
```

---

#### Step 3.8: Stop Generator
Press `Ctrl+C` in Terminal 3

---

#### Step 3.9: Collect Metrics
```bash
python3 analysis/collect_metrics_enhanced.py ysb-ctr-results-flink 45 500 results/spp_1000_flink.json
python3 analysis/collect_metrics_enhanced.py ysb-ctr-results-spark 45 500 results/spp_1000_spark.json
```

---

### TEST 3: MMPP (Alternating Load)

#### Step 3.10: Start MMPP Generator (Terminal 3)
```bash
python3 generators/mmpp_generator.py --low-rate 100 --high-rate 1000 --switch-interval 30 --stdout | \
    docker exec -i broker kafka-console-producer --bootstrap-server broker:29092 --topic ysb-events
```

---

#### Step 3.11: Let it Run
```bash
echo "Running MMPP test (3 minutes)..."
sleep 180
echo "Test complete!"
```

---

#### Step 3.12: Stop Generator
Press `Ctrl+C` in Terminal 3

---

#### Step 3.13: Collect Metrics
```bash
python3 analysis/collect_metrics_enhanced.py ysb-ctr-results-flink 45 500 results/mmpp_flink.json
python3 analysis/collect_metrics_enhanced.py ysb-ctr-results-spark 45 500 results/mmpp_spark.json
```

═══════════════════════════════════════════════════════════════════

## PHASE 4: GENERATE SUMMARY (2 minutes)

### Step 4.1: View All Results
```bash
ls -lh results/
```

**Expected**: Should see 6 JSON files (or 3 if Spark didn't work)

---

### Step 4.2: Quick Summary
```bash
echo "=== BENCHMARK RESULTS SUMMARY ==="
for file in results/*.json; do
    echo ""
    echo "File: $(basename $file)"
    python3 -c "import json; d=json.load(open('$file')); print(f\"  Samples: {d['sample_count']}, Mean: {d['latency_ms']['mean']:.2f}ms, P99: {d['latency_ms']['p99']:.2f}ms\")" 2>/dev/null || echo "  Error reading file"
done
```

---

### Step 4.3: Stop All Jobs
```bash
# In Terminal 1 (Flink): Press Ctrl+C
# In Terminal 2 (Spark): Press Ctrl+C
# Or from main terminal:
pkill -f "YSBCTRJob"
pkill -f "spark"
```

═══════════════════════════════════════════════════════════════════

## TROUBLESHOOTING

### If Kafka producer shows "disconnected" warnings:
- Wait longer (Kafka needs 60+ seconds to fully start)
- Check: `docker logs broker | tail -20`

### If Spark fails to start:
- That's OK! Focus on Flink benchmarks
- Document Spark's checkpoint issues in report

### If no metrics collected:
- Check if jobs are running: `ps aux | grep -E "flink|spark"`
- Verify data in Kafka: `docker exec broker kafka-console-consumer --bootstrap-server broker:29092 --topic ysb-ctr-results-flink --from-beginning --max-messages 5 --timeout-ms 5000`

═══════════════════════════════════════════════════════════════════

## FINAL CHECKLIST

- [ ] All 3 tests completed (SPP 100, SPP 1000, MMPP)
- [ ] JSON result files in results/ directory
- [ ] At least Flink metrics collected successfully
- [ ] Summary generated

═══════════════════════════════════════════════════════════════════

## NEXT STEPS

Once you have the results, I can:
1. Generate LaTeX tables from the JSON data
2. Update the report with actual metrics
3. Create comparison charts
4. Compile the final PDF report

═══════════════════════════════════════════════════════════════════

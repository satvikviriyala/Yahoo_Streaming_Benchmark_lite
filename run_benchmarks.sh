#!/bin/bash

#############################################################################
# Assignment 4: Comprehensive Benchmarking Pipeline
# 
# This script runs complete benchmarks for both Spark and Flink:
# - SPP Low Load (100 events/sec)
# - SPP High Load (1000 events/sec)  
# - MMPP (alternating 100/1000 events/sec)
#
# Results are saved to results/ directory in JSON format
#############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
JAVA_HOME="/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
export PATH="$JAVA_HOME/bin:$PATH"
RESULTS_DIR="results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Test durations (in seconds)
SPP_DURATION=120  # 2 minutes per SPP test
MMPP_DURATION=180 # 3 minutes for MMPP
COLLECTION_DURATION=60  # How long to collect metrics after generator stops

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Assignment 4: Comprehensive Benchmarking Pipeline        ║${NC}"
echo -e "${BLUE}║  Spark vs Flink - CTR Calculation Performance Analysis    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Create results directory
mkdir -p "$RESULTS_DIR"

#############################################################################
# Step 1: Clean Environment
#############################################################################
echo -e "${YELLOW}[1/9] Cleaning environment...${NC}"
pkill -9 -f "spp_generator" 2>/dev/null || true
pkill -9 -f "mmpp_generator" 2>/dev/null || true
pkill -9 -f "spark" 2>/dev/null || true
pkill -9 -f "flink" 2>/dev/null || true
pkill -9 -f "YSBCTRJob" 2>/dev/null || true
rm -rf /tmp/spark-checkpoints 2>/dev/null || true
mkdir -p /tmp/spark-checkpoints
echo -e "${GREEN}✓ Environment cleaned${NC}"

#############################################################################
# Step 2: Start Kafka Cluster
#############################################################################
echo -e "${YELLOW}[2/9] Starting Kafka cluster...${NC}"
docker-compose down 2>/dev/null || true
docker-compose up -d
echo "Waiting for Kafka to be ready..."
sleep 15
echo -e "${GREEN}✓ Kafka cluster started${NC}"

#############################################################################
# Step 3: Create Kafka Topics
#############################################################################
echo -e "${YELLOW}[3/9] Creating Kafka topics...${NC}"
docker exec broker kafka-topics --create --topic ysb-events \
    --bootstrap-server broker:29092 --partitions 1 --replication-factor 1 \
    --if-not-exists 2>/dev/null || true

docker exec broker kafka-topics --create --topic ysb-ctr-results-spark \
    --bootstrap-server broker:29092 --partitions 1 --replication-factor 1 \
    --if-not-exists 2>/dev/null || true

docker exec broker kafka-topics --create --topic ysb-ctr-results-flink \
    --bootstrap-server broker:29092 --partitions 1 --replication-factor 1 \
    --if-not-exists 2>/dev/null || true

echo -e "${GREEN}✓ Topics created${NC}"

#############################################################################
# Step 4: Start Spark Job
#############################################################################
echo -e "${YELLOW}[4/9] Starting Spark Structured Streaming job...${NC}"
nohup python3 spark/src/main.py > spark_benchmark.log 2>&1 &
SPARK_PID=$!
echo "Spark PID: $SPARK_PID"
sleep 10
if ps -p $SPARK_PID > /dev/null; then
    echo -e "${GREEN}✓ Spark job started successfully${NC}"
else
    echo -e "${RED}✗ Spark job failed to start. Check spark_benchmark.log${NC}"
    exit 1
fi

#############################################################################
# Step 5: Start Flink Job
#############################################################################
echo -e "${YELLOW}[5/9] Starting Flink DataStream job...${NC}"
cd flink
nohup mvn exec:java -Dexec.mainClass="org.example.YSBCTRJob" \
    -Djava.net.preferIPv4Stack=true > flink_benchmark.log 2>&1 &
FLINK_PID=$!
cd ..
echo "Flink PID: $FLINK_PID"
sleep 10
if ps -p $FLINK_PID > /dev/null; then
    echo -e "${GREEN}✓ Flink job started successfully${NC}"
else
    echo -e "${RED}✗ Flink job failed to start. Check flink/flink_benchmark.log${NC}"
    exit 1
fi

#############################################################################
# Function: Run Test and Collect Metrics
#############################################################################
run_test() {
    local test_name=$1
    local generator_cmd=$2
    local duration=$3
    
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  Running: $test_name${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # Start generator
    echo "Starting generator..."
    eval "$generator_cmd" &
    GEN_PID=$!
    
    # Wait for test duration
    echo "Running for ${duration}s..."
    sleep $duration
    
    # Stop generator
    kill $GEN_PID 2>/dev/null || true
    echo "Generator stopped. Waiting for pipeline to flush..."
    sleep 20
    
    # Collect metrics
    echo "Collecting Spark metrics..."
    python3 analysis/collect_metrics_enhanced.py ysb-ctr-results-spark \
        $COLLECTION_DURATION 500 "$RESULTS_DIR/${test_name}_spark.json" || echo "Warning: Spark metrics collection failed"
    
    echo "Collecting Flink metrics..."
    python3 analysis/collect_metrics_enhanced.py ysb-ctr-results-flink \
        $COLLECTION_DURATION 500 "$RESULTS_DIR/${test_name}_flink.json" || echo "Warning: Flink metrics collection failed"
    
    echo -e "${GREEN}✓ Test completed: $test_name${NC}"
}

#############################################################################
# Step 6: SPP Low Load Test (100 events/sec)
#############################################################################
echo -e "${YELLOW}[6/9] Running SPP Low Load Test (100 eps)...${NC}"
run_test "spp_100" \
    "python3 generators/spp_generator.py --rate 100 --stdout | docker exec -i broker kafka-console-producer --bootstrap-server broker:29092 --topic ysb-events" \
    $SPP_DURATION

#############################################################################
# Step 7: SPP High Load Test (1000 events/sec)
#############################################################################
echo -e "${YELLOW}[7/9] Running SPP High Load Test (1000 eps)...${NC}"
run_test "spp_1000" \
    "python3 generators/spp_generator.py --rate 1000 --stdout | docker exec -i broker kafka-console-producer --bootstrap-server broker:29092 --topic ysb-events" \
    $SPP_DURATION

#############################################################################
# Step 8: MMPP Test (alternating load)
#############################################################################
echo -e "${YELLOW}[8/9] Running MMPP Test (100/1000 eps alternating)...${NC}"
run_test "mmpp" \
    "python3 generators/mmpp_generator.py --low-rate 100 --high-rate 1000 --switch-interval 30 --stdout | docker exec -i broker kafka-console-producer --bootstrap-server broker:29092 --topic ysb-events" \
    $MMPP_DURATION

#############################################################################
# Step 9: Generate Summary Report
#############################################################################
echo -e "${YELLOW}[9/9] Generating summary report...${NC}"

cat > "$RESULTS_DIR/benchmark_summary_${TIMESTAMP}.txt" << EOF
╔════════════════════════════════════════════════════════════╗
║  Assignment 4: Benchmark Results Summary                  ║
║  Timestamp: $(date)                         ║
╚════════════════════════════════════════════════════════════╝

Test Configuration:
- SPP Duration: ${SPP_DURATION}s per test
- MMPP Duration: ${MMPP_DURATION}s
- Collection Duration: ${COLLECTION_DURATION}s
- Window Size: 10 seconds
- Watermark Delay: 5 seconds

Results Files:
$(ls -lh $RESULTS_DIR/*.json 2>/dev/null || echo "No JSON files found")

Quick Summary:
EOF

# Add quick stats from JSON files
for file in $RESULTS_DIR/*.json; do
    if [ -f "$file" ]; then
        echo "" >> "$RESULTS_DIR/benchmark_summary_${TIMESTAMP}.txt"
        echo "$(basename $file):" >> "$RESULTS_DIR/benchmark_summary_${TIMESTAMP}.txt"
        python3 -c "import json; data=json.load(open('$file')); print(f\"  Samples: {data.get('sample_count', 'N/A')}, Mean Latency: {data.get('latency_ms', {}).get('mean', 'N/A'):.2f}ms, P99: {data.get('latency_ms', {}).get('p99', 'N/A'):.2f}ms\")" 2>/dev/null >> "$RESULTS_DIR/benchmark_summary_${TIMESTAMP}.txt" || echo "  Error parsing file" >> "$RESULTS_DIR/benchmark_summary_${TIMESTAMP}.txt"
    fi
done

echo -e "${GREEN}✓ Summary report generated${NC}"

#############################################################################
# Cleanup
#############################################################################
echo ""
echo -e "${YELLOW}Stopping jobs...${NC}"
kill $SPARK_PID 2>/dev/null || true
kill $FLINK_PID 2>/dev/null || true

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✓ Benchmarking Complete!                                 ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Results saved to: ${BLUE}$RESULTS_DIR/${NC}"
echo -e "Summary report: ${BLUE}$RESULTS_DIR/benchmark_summary_${TIMESTAMP}.txt${NC}"
echo ""
echo "To view results:"
echo "  cat $RESULTS_DIR/benchmark_summary_${TIMESTAMP}.txt"
echo "  cat $RESULTS_DIR/spp_100_spark.json"
echo "  cat $RESULTS_DIR/spp_100_flink.json"
echo ""

#!/bin/bash

# Assignment 4 - Stream Processing Pipeline Runner
# This script starts the complete pipeline: Kafka, Spark, Flink, and Generator

set -e

echo "=== Starting Assignment 4 Stream Processing Pipeline ==="

# Set Java Home
export JAVA_HOME="/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
export PATH="$JAVA_HOME/bin:$PATH"

# Start Kafka cluster
echo "1. Starting Kafka cluster..."
docker-compose up -d
sleep 10

# Create topics
echo "2. Creating Kafka topics..."
docker exec broker kafka-topics --create --topic ysb-events --bootstrap-server broker:29092 --partitions 1 --replication-factor 1 --if-not-exists
docker exec broker kafka-topics --create --topic ysb-ctr-results-spark --bootstrap-server broker:29092 --partitions 1 --replication-factor 1 --if-not-exists
docker exec broker kafka-topics --create --topic ysb-ctr-results-flink --bootstrap-server broker:29092 --partitions 1 --replication-factor 1 --if-not-exists

# Start Spark job
echo "3. Starting Spark Structured Streaming job..."
python3 spark/src/main.py > spark.log 2>&1 &
SPARK_PID=$!
echo "   Spark PID: $SPARK_PID"
sleep 5

# Start Flink job
echo "4. Starting Flink DataStream job..."
cd flink && mvn exec:java -Dexec.mainClass="org.example.YSBCTRJob" -Djava.net.preferIPv4Stack=true > flink.log 2>&1 &
FLINK_PID=$!
cd ..
echo "   Flink PID: $FLINK_PID"
sleep 5

# Start generator
echo "5. Starting SPP Generator (100 events/sec)..."
python3 generators/spp_generator.py --rate 100 --stdout | docker exec -i broker kafka-console-producer --bootstrap-server broker:29092 --topic ysb-events &
GEN_PID=$!
echo "   Generator PID: $GEN_PID"

echo ""
echo "=== Pipeline Started Successfully ==="
echo "Spark PID: $SPARK_PID (logs: spark.log)"
echo "Flink PID: $FLINK_PID (logs: flink/flink.log)"
echo "Generator PID: $GEN_PID"
echo ""
echo "To verify output, run:"
echo "  docker exec broker kafka-console-consumer --bootstrap-server broker:29092 --topic ysb-ctr-results-spark --from-beginning --max-messages 5"
echo "  docker exec broker kafka-console-consumer --bootstrap-server broker:29092 --topic ysb-ctr-results-flink --from-beginning --max-messages 5"
echo ""
echo "To stop the pipeline:"
echo "  kill $SPARK_PID $FLINK_PID $GEN_PID"
echo "  docker-compose down"

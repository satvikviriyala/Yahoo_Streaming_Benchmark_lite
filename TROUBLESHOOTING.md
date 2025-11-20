# Troubleshooting Guide

## Issue: Kafka Connection Timeout

### Symptoms
- Spark/Flink jobs fail with `TimeoutException: Timed out waiting for a node assignment`
- Error: `Failed to get metadata for topics`

### Root Cause
The `KAFKA_LISTENERS` environment variable was missing from the Docker Compose configuration. This prevented external clients (Spark/Flink running on the host) from connecting to Kafka running inside Docker.

### Solution
Added the following line to `docker-compose.yml`:
```yaml
KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:29092,PLAINTEXT_HOST://0.0.0.0:9092
```

This configures Kafka to listen on:
- `PLAINTEXT://0.0.0.0:29092` - Internal Docker network (for broker-to-broker and internal clients)
- `PLAINTEXT_HOST://0.0.0.0:9092` - External host network (mapped to port 9093 on host)

### Verification
After fixing, you should see:
1. Spark successfully connecting to Kafka at `127.0.0.1:9093`
2. Flink successfully connecting to Kafka at `127.0.0.1:9093`
3. CTR results appearing in output topics

## Issue: IPv6 vs IPv4 Resolution

### Symptoms
- Connection works with `127.0.0.1` but fails with `localhost`

### Solution
Added JVM option to force IPv4:
- Spark: `.config("spark.driver.extraJavaOptions", "-Djava.net.preferIPv4Stack=true")`
- Flink: `mvn exec:java -Djava.net.preferIPv4Stack=true`

## Quick Health Check

```bash
# 1. Check Kafka is running
docker ps | grep broker

# 2. Check topics exist
docker exec broker kafka-topics --list --bootstrap-server broker:29092

# 3. Test producer (should not timeout)
echo '{"test": "message"}' | docker exec -i broker kafka-console-producer --bootstrap-server broker:29092 --topic ysb-events

# 4. Test consumer (should show the test message)
docker exec broker kafka-console-consumer --bootstrap-server broker:29092 --topic ysb-events --from-beginning --max-messages 1 --timeout-ms 5000

# 5. Check Spark output
docker exec broker kafka-console-consumer --bootstrap-server broker:29092 --topic ysb-ctr-results-spark --from-beginning --max-messages 3 --timeout-ms 10000

# 6. Check Flink output
docker exec broker kafka-console-consumer --bootstrap-server broker:29092 --topic ysb-ctr-results-flink --from-beginning --max-messages 3 --timeout-ms 10000
```

## Port Configuration

- **9093** (host) → **9092** (container): External clients (Spark/Flink on host)
- **29092** (container): Internal Docker network
- **2181**: Zookeeper
- **9102** (host) → **9101** (container): JMX metrics

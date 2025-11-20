#!/usr/bin/env python3
import subprocess
import json
import time
import sys

def collect_and_analyze(topic, duration=30):
    """Collect data from Kafka topic and calculate latency statistics"""
    print(f"Collecting from {topic} for {duration}s...")
    
    cmd = [
        "docker", "exec", "broker",
        "kafka-console-consumer",
        "--bootstrap-server", "broker:29092",
        "--topic", topic,
        "--from-beginning",
        "--timeout-ms", str(duration * 1000)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=duration + 5)
        lines = result.stdout.strip().split('\n')
        
        latencies = []
        for line in lines:
            if not line or line.startswith('[') or 'Processed' in line:
                continue
            try:
                data = json.loads(line)
                if 'result_generation_time_ms' in data or 'resultGenerationTimeMs' in data:
                    # Handle both Spark and Flink field naming
                    gen_time = data.get('result_generation_time_ms') or data.get('resultGenerationTimeMs')
                    min_time = data.get('min_insertion_time_ms') or data.get('minInsertionTimeMs')
                    if gen_time and min_time:
                        latency = gen_time - min_time
                        latencies.append(latency)
            except json.JSONDecodeError:
                continue
        
        if not latencies:
            return None
        
        latencies.sort()
        n = len(latencies)
        
        return {
            'count': n,
            'mean': sum(latencies) / n,
            'median': latencies[n // 2],
            'p95': latencies[int(n * 0.95)] if n > 20 else latencies[-1],
            'p99': latencies[int(n * 0.99)] if n > 100 else latencies[-1],
            'min': latencies[0],
            'max': latencies[-1]
        }
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: collect_metrics.py <topic> [duration]")
        sys.exit(1)
    
    topic = sys.argv[1]
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    
    stats = collect_and_analyze(topic, duration)
    
    if stats:
        print(f"\n=== Metrics for {topic} ===")
        print(f"Samples: {stats['count']}")
        print(f"Mean Latency: {stats['mean']:.2f} ms")
        print(f"Median Latency: {stats['median']:.2f} ms")
        print(f"P95 Latency: {stats['p95']:.2f} ms")
        print(f"P99 Latency: {stats['p99']:.2f} ms")
        print(f"Min: {stats['min']:.2f} ms, Max: {stats['max']:.2f} ms")
        
        # Output JSON for easy parsing
        print(f"\nJSON: {json.dumps(stats)}")
    else:
        print(f"No data collected from {topic}")
        sys.exit(1)

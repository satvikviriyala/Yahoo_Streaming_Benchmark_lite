#!/usr/bin/env python3
"""
Enhanced metrics collection script for Assignment 4
Collects latency statistics from Kafka output topics
Supports both Spark and Flink output formats
"""
import subprocess
import json
import time
import sys
import statistics

def collect_and_analyze(topic, duration=45, max_samples=1000):
    """Collect data from Kafka topic and calculate comprehensive latency statistics"""
    print(f"📊 Collecting from {topic} for {duration}s (max {max_samples} samples)...")
    
    cmd = [
        "docker", "exec", "broker",
        "kafka-console-consumer",
        "--bootstrap-server", "broker:29092",
        "--topic", topic,
        "--from-beginning",
        "--max-messages", str(max_samples),
        "--timeout-ms", str(duration * 1000)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=duration + 10)
        lines = result.stdout.strip().split('\n')
        
        latencies = []
        windows = []
        
        for line in lines:
            if not line or line.startswith('[') or 'Processed' in line:
                continue
            try:
                data = json.loads(line)
                
                # Handle both Spark and Flink field naming
                gen_time = data.get('result_generation_time_ms') or data.get('resultGenerationTimeMs')
                min_time = data.get('min_insertion_time_ms') or data.get('minInsertionTimeMs')
                window_end = data.get('window_end_time') or data.get('windowEndTime')
                
                if gen_time and min_time:
                    latency = gen_time - min_time
                    latencies.append(latency)
                    if window_end:
                        windows.append(window_end)
                        
            except json.JSONDecodeError:
                continue
        
        if not latencies:
            print(f"⚠️  No valid data collected from {topic}")
            return None
        
        latencies.sort()
        n = len(latencies)
        
        stats = {
            'topic': topic,
            'sample_count': n,
            'window_count': len(set(windows)) if windows else n,
            'latency_ms': {
                'mean': statistics.mean(latencies),
                'median': statistics.median(latencies),
                'stdev': statistics.stdev(latencies) if n > 1 else 0,
                'min': min(latencies),
                'max': max(latencies),
                'p50': latencies[int(n * 0.50)],
                'p95': latencies[int(n * 0.95)] if n > 20 else latencies[-1],
                'p99': latencies[int(n * 0.99)] if n > 100 else latencies[-1],
            },
            'collection_duration_s': duration,
            'timestamp': time.time()
        }
        
        return stats
        
    except subprocess.TimeoutExpired:
        print(f"⏱️  Collection timed out after {duration}s")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def print_stats(stats):
    """Pretty print statistics"""
    if not stats:
        return
        
    print(f"\n{'='*60}")
    print(f"📈 Metrics for {stats['topic']}")
    print(f"{'='*60}")
    print(f"Samples Collected: {stats['sample_count']}")
    print(f"Windows Processed: {stats['window_count']}")
    print(f"\nLatency Statistics (ms):")
    print(f"  Mean:   {stats['latency_ms']['mean']:.2f}")
    print(f"  Median: {stats['latency_ms']['median']:.2f}")
    print(f"  StdDev: {stats['latency_ms']['stdev']:.2f}")
    print(f"  Min:    {stats['latency_ms']['min']:.2f}")
    print(f"  Max:    {stats['latency_ms']['max']:.2f}")
    print(f"  P50:    {stats['latency_ms']['p50']:.2f}")
    print(f"  P95:    {stats['latency_ms']['p95']:.2f}")
    print(f"  P99:    {stats['latency_ms']['p99']:.2f}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: collect_metrics_enhanced.py <topic> [duration] [max_samples] [output_file]")
        sys.exit(1)
    
    topic = sys.argv[1]
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 45
    max_samples = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
    output_file = sys.argv[4] if len(sys.argv) > 4 else None
    
    stats = collect_and_analyze(topic, duration, max_samples)
    
    if stats:
        print_stats(stats)
        
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(stats, f, indent=2)
            print(f"✅ Results saved to {output_file}")
        else:
            print(f"\n📄 JSON Output:\n{json.dumps(stats, indent=2)}")
        
        sys.exit(0)
    else:
        print(f"❌ Failed to collect metrics from {topic}")
        sys.exit(1)

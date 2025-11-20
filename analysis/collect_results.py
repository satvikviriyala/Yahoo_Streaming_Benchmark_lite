import subprocess
import time
import json
import numpy as np
import argparse

def collect_data(topic, duration, output_file):
    print(f"Collecting data from {topic} for {duration} seconds...")
    cmd = [
        "docker", "exec", "broker", 
        "kafka-console-consumer", 
        "--bootstrap-server", "broker:29092", 
        "--topic", topic, 
        "--timeout-ms", str(duration * 1000)
    ]
    
    with open(output_file, "w") as f:
        try:
            subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, timeout=duration + 5)
        except subprocess.TimeoutExpired:
            pass
            
    print(f"Data saved to {output_file}")

def analyze_data(input_file):
    latencies = []
    with open(input_file, "r") as f:
        for line in f:
            try:
                if not line.strip(): continue
                data = json.loads(line)
                if "result_generation_time_ms" in data and "min_insertion_time_ms" in data:
                    latency = data["result_generation_time_ms"] - data["min_insertion_time_ms"]
                    latencies.append(latency)
            except json.JSONDecodeError:
                continue
                
    if not latencies:
        print("No valid data found.")
        return None
        
    latencies = np.array(latencies)
    stats = {
        "mean": np.mean(latencies),
        "median": np.median(latencies),
        "p95": np.percentile(latencies, 95),
        "p99": np.percentile(latencies, 99),
        "count": len(latencies)
    }
    print(f"Stats for {input_file}: {stats}")
    return stats

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    
    collect_data(args.topic, args.duration, args.output)
    analyze_data(args.output)

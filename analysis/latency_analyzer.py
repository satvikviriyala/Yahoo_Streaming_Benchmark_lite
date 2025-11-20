import json
import argparse
import numpy as np
from kafka import KafkaConsumer

def analyze_latency(bootstrap_servers, topic, num_messages=100):
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        auto_offset_reset='earliest',
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        consumer_timeout_ms=10000,
        api_version=(2, 5, 0)
    )

    latencies = []
    print(f"Listening to {topic}...")

    try:
        for message in consumer:
            data = message.value
            # End-to-end latency = Result Generation Time - Min Insertion Time of events in window
            # Note: This is a simplified metric. Ideally we'd track per-event latency, but window-level is sufficient for A4.
            if 'result_generation_time_ms' in data and 'min_insertion_time_ms' in data:
                latency = data['result_generation_time_ms'] - data['min_insertion_time_ms']
                latencies.append(latency)
                print(f"Window: {data.get('window_end_time')} | Latency: {latency} ms | CTR: {data.get('ctr'):.4f}")

            if len(latencies) >= num_messages:
                break
    except Exception as e:
        print(f"Error: {e}")
    finally:
        consumer.close()

    if latencies:
        print("\n--- Latency Statistics (ms) ---")
        print(f"Count: {len(latencies)}")
        print(f"Mean: {np.mean(latencies):.2f}")
        print(f"Median: {np.median(latencies):.2f}")
        print(f"P95: {np.percentile(latencies, 95):.2f}")
        print(f"P99: {np.percentile(latencies, 99):.2f}")
        print(f"Min: {np.min(latencies)}")
        print(f"Max: {np.max(latencies)}")
    else:
        print("No messages received.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Latency Analyzer")
    parser.add_argument("--bootstrap-servers", default="localhost:9093", help="Kafka bootstrap servers")
    parser.add_argument("--topic", required=True, help="Output topic to analyze")
    parser.add_argument("--count", type=int, default=100, help="Number of messages to analyze")
    
    args = parser.parse_args()
    analyze_latency(args.bootstrap_servers, args.topic, args.count)

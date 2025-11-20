import time
import json
import argparse
import random
import numpy as np
import time
import random
import argparse
import sys
from kafka import KafkaProducer
from event_schema import generate_event

def run_generator(bootstrap_servers, topic, low_rate, high_rate, switch_interval, use_stdout=False):
    print(f"Starting MMPP Generator: Low={low_rate}, High={high_rate}, Interval={switch_interval}s")
    
    producer = None
    if not use_stdout:
        for _ in range(10):
            try:
                producer = KafkaProducer(
                    bootstrap_servers=bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8')
                )
                break
            except Exception as e:
                print(f"Waiting for Kafka... ({e})")
                time.sleep(5)
                
        if not producer:
            print("Failed to connect to Kafka")
            return
    
    current_rate = low_rate
    last_switch = time.time()
    
    try:
        while True:
            now = time.time()
            if now - last_switch >= switch_interval:
                current_rate = high_rate if current_rate == low_rate else low_rate
                last_switch = now
                print(f"Switched rate to {current_rate}")
            
            wait_time = random.expovariate(current_rate)
            time.sleep(wait_time)
            
            event = generate_event()
            
            if use_stdout:
                print(json.dumps(event))
                sys.stdout.flush()
            else:
                producer.send(topic, event)
                
    except KeyboardInterrupt:
        print("Stopping generator...")
        if producer:
            producer.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MMPP Data Generator")
    parser.add_argument("--bootstrap-servers", default="127.0.0.1:9093", help="Kafka bootstrap servers")
    parser.add_argument("--stdout", action="store_true", help="Print to stdout instead of Kafka")
    parser.add_argument("--topic", default="ysb-events", help="Kafka topic")
    parser.add_argument("--low-rate", type=float, default=100.0, help="Low state events per second")
    parser.add_argument("--high-rate", type=float, default=1000.0, help="High state events per second")
    parser.add_argument("--switch-interval", type=float, default=60.0, help="Seconds between state switches")
    
    args = parser.parse_args()
    
    run_generator(args.bootstrap_servers, args.topic, args.low_rate, args.high_rate, args.switch_interval, args.stdout)

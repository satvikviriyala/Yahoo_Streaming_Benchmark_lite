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

def run_generator(bootstrap_servers, topic, rate, use_stdout=False): # Modified function signature
    print(f"Starting SPP Generator: Target Rate = {rate} events/sec")
    
    producer = None
    if not use_stdout: # Added conditional block for Kafka producer
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
    
    try:
        while True:
            # Poisson process inter-arrival time
            wait_time = random.expovariate(rate) # Changed from np.random.exponential
            time.sleep(wait_time)
            
            event = generate_event()
            
            if use_stdout: # Added conditional output logic
                print(json.dumps(event))
                sys.stdout.flush()
            else:
                producer.send(topic, event)
                # print(f"Sent event: {event['event_time']}") # Verbose
                
    except KeyboardInterrupt:
        print("Stopping generator...")
        if producer: # Modified producer close logic
            producer.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SPP Data Generator")
    parser.add_argument("--bootstrap-servers", default="127.0.0.1:9093", help="Kafka bootstrap servers")
    parser.add_argument("--stdout", action="store_true", help="Print to stdout instead of Kafka")
    parser.add_argument("--topic", default="ysb-events", help="Kafka topic")
    parser.add_argument("--rate", type=float, default=100.0, help="Events per second")
    
    args = parser.parse_args()
    
    run_generator(args.bootstrap_servers, args.topic, args.rate, args.stdout) # Modified function call

from kafka import KafkaConsumer
import json
import datetime

import socket

def check_port(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((host, port))
    sock.close()
    return result == 0

def debug_topic(topic):
    print(f"--- Debugging Topic: {topic} ---")
    host = '127.0.0.1'
    port = 9093
    if check_port(host, port):
        print(f"Port {port} is OPEN")
    else:
        print(f"Port {port} is CLOSED")
        return

    try:
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=f'{host}:{port}',
            auto_offset_reset='earliest',
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            consumer_timeout_ms=5000
        )
        
        print(f"Available Topics: {consumer.topics()}")
        
        count = 0
        for msg in consumer:
            print(f"Msg {count}: {msg.value}")
            if 'event_time' in msg.value:
                et = datetime.datetime.fromtimestamp(msg.value['event_time'])
                print(f"  Event Time: {et}")
            count += 1
            if count >= 5:
                break
        
        if count == 0:
            print("NO MESSAGES FOUND.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_topic("ysb-events")
    debug_topic("ysb-ctr-results-spark")
    debug_topic("ysb-ctr-results-flink")

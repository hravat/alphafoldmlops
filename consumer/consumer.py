import os
import json
import time
import requests
from confluent_kafka import Consumer, KafkaException, KafkaError


print("Starting Consumer ")
# ─── Config ────────────────────────────────────────────────────────────────────
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9094")
KAFKA_TOPIC            = os.getenv("KAFKA_TOPIC", "sdv_stream")
GROUP_ID               = os.getenv("CONSUMER_GROUP", "prediction-consumer")

# Map a model name ➜ REST endpoint
MODEL_ENDPOINTS = {
    "model-server-rf":  "http://model-server-rf:8000/invocations"
    #"ChemblPredictor2": "http://model-server2:8000/invocations",
    # add more here
}

# ─── Create Confluent Kafka consumer ───────────────────────────────────────────
conf = {
    "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
    "group.id": GROUP_ID,
    "auto.offset.reset": "latest",
    "enable.auto.commit": True,
}

consumer = Consumer(conf)
consumer.subscribe([KAFKA_TOPIC])
print(f"Connected to Kafka {KAFKA_BOOTSTRAP_SERVERS}, topic '{KAFKA_TOPIC}'")


# ─── Helper to call model REST API ─────────────────────────────────────────────
def call_model(model_name: str, features: dict):
    endpoint = MODEL_ENDPOINTS.get(model_name)
    if not endpoint:
        print(f"[WARN] Unknown model '{model_name}', skipping...")
        return
    payload = {"inputs": [features]}
    try:
        print(f"→ Calling model '{model_name}' with payload: {payload}")
        start_time = time.time()
        response = requests.post(endpoint, json=payload, timeout=5)
        response.raise_for_status()
        latency = time.time() - start_time
        print(f"[{model_name}] {latency:.3f}s → Prediction: {response.json()}")
    except Exception as e:
        print(f"[ERROR] Failed to call model '{model_name}': {e}")

## ─── Consume loop ──────────────────────────────────────────────────────────────
try:
    while True:
        msg = consumer.poll(1.0)  # 1-second timeout
        if msg is None:
            continue  # no message this poll
        if msg.error():
            if msg.error().code() != KafkaError._PARTITION_EOF:
                print(f"[ERROR] {msg.error()}")
            continue

        # Print raw Kafka message value (decoded)
        kafka_message=msg.value().decode('utf-8')
        payload = json.loads(kafka_message)
        print(f"[KAFKA MESSAGE] {kafka_message}")

        # You can add your message processing logic here
        call_model("model-server-rf", payload)

except KeyboardInterrupt:
    print("Stopping consumer…")
finally:
    consumer.close()


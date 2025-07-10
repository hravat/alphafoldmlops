import os
import json
import time
import requests
from confluent_kafka import Consumer, KafkaException, KafkaError
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
import math

PUSHGATEWAY_URL = os.getenv("PUSHGATEWAY_URL", "http://pushgateway:9091")


def is_valid_features(features: dict):
    for value in features.values():
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return False
    return True


def push_all_predictions_to_gateway(predictions: dict):
    registry = CollectorRegistry()
    g = Gauge('model_prediction', 'Prediction value from model', ['model_name'], registry=registry)
    for model_name, prediction in predictions.items():
        if prediction is None or prediction == -9999:
            continue
        g.labels(model_name=model_name).set(prediction)
    try:
        push_to_gateway(PUSHGATEWAY_URL, 
                        job='ml_predictions', 
                        registry=registry,
                        grouping_key={"predictions": "ml_predictions"},
                        )
        print(f"[PUSHED] Batch predictions: {predictions}")
    except Exception as e:
        print(f"[ERROR] Failed to push batch predictions: {e}")


print("Starting Consumer ")
# ─── Config ────────────────────────────────────────────────────────────────────
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9094")
KAFKA_TOPIC            = os.getenv("KAFKA_TOPIC", "sdv_stream")
GROUP_ID               = os.getenv("CONSUMER_GROUP", "prediction-consumer")

# Map a model name ➜ REST endpoint
MODEL_ENDPOINTS = {
    "model-server-rf":  "http://model-server-rf:8000/invocations",
    "model-server-nn":  "http://model-server-nn:8000/invocations",
    "model-server-xgboost":  "http://model-server-xgboost:8000/invocations",
    "model-server-sgd":  "http://model-server-sgd:8000/invocations"
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
    
    if not is_valid_features(features):
        print(f"[SKIP] Invalid values in features for model '{model_name}', skipping prediction.")
        return -9999
    
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
        prediction = response.json()["predictions"][0] 
        return prediction
    except Exception as e:
        print(f"[ERROR] Failed to call model '{model_name}': {e}")
        return None
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
        
        
        standard_value=payload.get("standard_value", -9999)
        

        # You can add your message processing logic here
        rf_prediction=call_model("model-server-rf", payload)
        nn_prediction=call_model("model-server-nn", payload)
        sgd_prediction=call_model("model-server-sgd", payload)
        xgboost_prediction=call_model("model-server-xgboost", payload)
        
        
        preds = {
        "rf": rf_prediction,
        "nn": nn_prediction,
        "sgd": sgd_prediction,
        "xgboost": xgboost_prediction,
        "target":standard_value
        }
        
        push_all_predictions_to_gateway(preds)
        
except KeyboardInterrupt:
    print("Stopping consumer…")
finally:
    consumer.close()


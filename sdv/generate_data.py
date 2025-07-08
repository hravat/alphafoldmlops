"""
simulate_sdv_stream.py
Generate synthetic data with SDV and stream the rows
"""

import os
import time
import json
import argparse
import pandas as pd
import psycopg2
import requests
import numpy as np

from sdv.single_table import CTGANSynthesizer
from sdv.metadata import SingleTableMetadata
from confluent_kafka import Producer
import json


def get_connection():
    """
    Open a psycopg2 connection using the env vars defined in docker-compose:
    ML_DATASET_DBNAME, POSTGRES_SCHEMA, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT
    """
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("ML_DATASET_DBNAME", "postgres"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        options=f"-c search_path={os.getenv('POSTGRES_SCHEMA', 'public')}",
        connect_timeout=10
    )
    return conn

def fetch_sample(table_name: str, sample_size: int = 100000) -> pd.DataFrame:
    """Pull a random sample so the full table need not load into memory."""
    sql = f"""
        select "mw_freebase", "alogp", "hba", "hbd" ,"standard_value"
        from public.chembl_ml_dataset c 
        where "standard_value" is not null 
        LIMIT {sample_size}
    """
    with get_connection() as conn:
        df = pd.read_sql(sql, conn)
    return df

def generate_synthetic_data(df: pd.DataFrame, batch_size: int) -> pd.DataFrame:
    """
    Generate synthetic data using ranges, categories, or datetime ranges.
    """
    
    metadata = SingleTableMetadata()
    metadata.detect_from_dataframe(data=df)
    synthesizer = CTGANSynthesizer(metadata)
    synthesizer.fit(df)

    synthetic_data = synthesizer.sample(num_rows=10)
    print(synthetic_data.head())
    
    print('Succesful data generation')
    
    return synthesizer
    
def stream_rows(synthesizer):
    """
    Stream one row at a time with a specified delay (in seconds).
    """
    synthetic_data = synthesizer.sample(num_rows=1) 
    return synthetic_data


# -----------------------------------------------------------------------------
# Kafka helpers
# -----------------------------------------------------------------------------
KAFKA_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9094")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "sdv_stream")
producer = Producer({"bootstrap.servers": KAFKA_SERVERS})


def publish_row(record: dict):
    """Serialize and send a single record to Kafka."""
    try:
        producer.produce(KAFKA_TOPIC, json.dumps(record).encode())
    except BufferError:
        producer.poll(0.1)  # allow queue to empty
        producer.produce(KAFKA_TOPIC, json.dumps(record).encode())




def main():
    batch_size = 100
    delay = float(os.getenv("SAMPLE_INTERVAL", "1"))
    table_name = "public.chembl_ml_dataset"
    sample_size = 10000  # number of rows to fetch from DB for training

    print("Fetching sample data...")
    df = fetch_sample(table_name, sample_size)

    print("Training SDV CTGAN model...")
    synthesizer = generate_synthetic_data(df, batch_size)
    print("Model training complete. Starting synthetic data stream...")

    while True:
        synthetic_data = stream_rows(synthesizer)
        record = synthetic_data.iloc[0].to_dict()
        publish_row(record)
        print("Stream data")
        print(synthetic_data.head())
        time.sleep(delay)


if __name__ == "__main__":
    main()

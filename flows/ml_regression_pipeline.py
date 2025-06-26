from prefect import flow, task , get_run_logger
import httpx
import time
import uuid
from sqlalchemy import create_engine, text


def get_row_count_sqlalchemy(table_name):
    db_url = "postgresql+psycopg2://postgres:postgres%40123@postgres:5432/chembl_db"
    engine = create_engine(db_url)

    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name} WHERE standard_value is not null;"))
        count = result.scalar()  # returns single value
    return count

@task
def trigger_mage(batch_num,run_uuid, row_start, row_end, is_last_batch):

    logger = get_run_logger()
    url = "http://mage:6789/api/pipeline_schedules/1/pipeline_runs/5b9ad51754e5488ebdeb4513b7489538"
    
    payload = {
        "pipeline_run": {
            "variables": {
                "row_start": row_start,
                "row_end": row_end,
                "run_uuid": run_uuid,
                "is_last_batch": is_last_batch
            }
        }
    }

    logger.info(f"Triggering Mage for batch {batch_num} | Rows {row_start} to {row_end}")
    print("Payload being sent to Mage:", payload) 
    response = httpx.post(url, json=payload)
    
    response.raise_for_status()
    run_data = response.json()
    print("Mage pipeline triggered:", run_data)
    
    print("Status code:", response.status_code)
    print("Response body:", response.text)

    # Extract pipeline run ID to poll status
    pipeline_run_id = run_data.get('pipeline_run', {}).get('id')
    if not pipeline_run_id:
        raise Exception("No pipeline run ID returned from trigger.")
    
    status = 'running'
    while status == 'running':
        time.sleep(10)  # wait before polling again
        status_check = httpx.get(f"http://mage:6789/api/pipeline_runs/{pipeline_run_id}")
        status_check.raise_for_status()
        status = status_check.json().get('pipeline_run', {}).get('status')
        print(f"Batch {batch_num} status: {status}")
    
    if status != 'completed':
        raise Exception(f"Batch {batch_num} failed with status: {status}")
    
    print(f"Batch {batch_num} completed successfully")

@flow
def ml_regerssion_pipeline():
    
    run_uuid = str(uuid.uuid4()) 
    table_name='public.chembl_ml_dataset'

    total_rows = get_row_count_sqlalchemy(table_name)
    logger = get_run_logger()
    logger.info(f"Total rows in {table_name}: {total_rows}")

    print(f"Total rows in {table_name}: {total_rows}")

    batch_size = total_rows // 10

    is_last_batch=False 

    for batch_num in range(10):
        row_start = batch_num * batch_size + 1
        row_end = (batch_num + 1) * batch_size if batch_num < 9 else total_rows
        
        if batch_num==4:
            is_last_batch=True

        logger.info(f"Preparing batch {batch_num} rows {row_start} to {row_end}")
        trigger_mage(batch_num, run_uuid, row_start, row_end ,is_last_batch)
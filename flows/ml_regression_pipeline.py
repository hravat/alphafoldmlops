from prefect import flow, task
import httpx
import time
import uuid

@task
def trigger_mage(batch_num,run_uuid):
    url = "http://mage:6789/api/pipeline_schedules/1/pipeline_runs/5b9ad51754e5488ebdeb4513b7489538"
    offset = 10
    limit = 100
    
    
    payload = {
        "pipeline_run": {
            "variables": {
                "offset": offset,
                "limit": limit,
                "run_uuid": run_uuid
            }
        }
    }

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
    for batch_num in range(5):
        trigger_mage(batch_num,run_uuid)
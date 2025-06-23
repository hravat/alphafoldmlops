from prefect import flow, task
import subprocess
import httpx
import time

@task
def trigger_mage(batch_num):
    print(f"Triggering batch {batch_num}")
    url = "http://mage:6789/api/pipeline_schedules/1/pipeline_runs/5bed182853a745968bc6c00c68c2de69"
    r = httpx.post(url)
    r.raise_for_status()
    run_data = r.json()
    print("Mage pipeline triggered:", run_data)
    
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
def run_mage_batches():
    for batch_num in range(3):
        trigger_mage(batch_num)

if __name__ == "__main__":
    run_mage_batches()
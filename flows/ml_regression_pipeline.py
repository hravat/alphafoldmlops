from prefect import flow, task
import httpx
import time
import uuid

@task
def trigger_mage():
    url = "http://mage:6789/api/pipeline_schedules/1/pipeline_runs/3b3832eb8caa46ffb5fdcbab06f48681"
    offset = 10
    limit = 100
    run_uuid = str(uuid.uuid4()) 
    
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

    print("Status code:", response.status_code)
    print("Response body:", response.text)

    response.raise_for_status()  # Will raise an error if request failed

@flow
def ml_regerssion_pipeline():
    for i in range(1):
        trigger_mage()
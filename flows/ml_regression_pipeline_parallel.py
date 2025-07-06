from prefect import flow, task, get_run_logger
import httpx, time, uuid
from sqlalchemy import create_engine, text

# ---------- utility task ----------------------------------------------------
def get_row_count_sqlalchemy(table_name: str) -> int:
    db_url = "postgresql+psycopg2://postgres:postgres%40123@postgres:5432/chembl_db"
    engine = create_engine(db_url)
    with engine.connect() as conn:
        result = conn.execute(
            text(f"SELECT COUNT(*) FROM {table_name} WHERE standard_value is not null;")
        )
        return result.scalar()

# ---------- task that calls Mage -------------------------------------------
@task(retries=2, retry_delay_seconds=10)
def trigger_mage(
    batch_num: int,
    run_uuid: str,
    row_start: int,
    row_end: int,
    is_last_batch: bool,
    model_type: str,
    params: dict,
):
    logger = get_run_logger()
    url = (
        "http://mage:6789/api/pipeline_schedules/"
        "1/pipeline_runs/5b9ad51754e5488ebdeb4513b7489538"
    )

    payload = {
        "pipeline_run": {
            "variables": {
                "row_start": row_start,
                "row_end": row_end,
                "run_uuid": run_uuid,
                "is_last_batch": is_last_batch,
                "model_type": model_type,
                "params": params,
            }
        }
    }

    logger.info(f"Triggering Mage for batch {batch_num} ({row_start}–{row_end})")
    r = httpx.post(url, json=payload, timeout=30)
    r.raise_for_status()
    pipeline_run_id = r.json().get("pipeline_run", {}).get("id")
    if not pipeline_run_id:
        raise ValueError("No pipeline run ID returned from Mage")

    status = "running"
    while status == "running":
        time.sleep(10)
        check = httpx.get(f"http://mage:6789/api/pipeline_runs/{pipeline_run_id}")
        check.raise_for_status()
        status = check.json().get("pipeline_run", {}).get("status")
        logger.info(f"Batch {batch_num} status: {status}")

    if status != "completed":
        raise RuntimeError(f"Batch {batch_num} failed with status {status}")

# ---------- sub‑flow, one per model‑parameter pair --------------------------
@flow(name="run_model_combo", task_runner="subprocess")
def run_model_combo(model_type: str, params: dict, total_rows: int, batches: int):
    logger = get_run_logger()
    batch_size = total_rows // batches
    run_uuid = str(uuid.uuid4())

    for batch_num in range(batches):
        row_start = batch_num * batch_size + 1
        row_end = min((batch_num + 1) * batch_size, total_rows)
        is_last_batch = batch_num == batches - 1

        logger.info(
            f"Model {model_type} {params} — batch {batch_num}, rows {row_start}:{row_end}"
        )
        trigger_mage(
            batch_num,
            run_uuid,
            row_start,
            row_end,
            is_last_batch,
            model_type,
            params,
        )

# ---------- top‑level flow ---------------------------------------------------
@flow
def ml_regression_pipeline_parallel():
    table_name = "public.chembl_ml_dataset"
    total_rows = get_row_count_sqlalchemy(table_name)
    logger = get_run_logger()
    logger.info(f"Total rows in {table_name}: {total_rows}")

    batches = 5

    # -------- grid search space ---------------------------------------------
    rf_grid = [{"max_depth": d} for d in [3, 5, 7]]
    xgb_grid = [{"eta": e} for e in [0.05, 0.1, 0.3]]
    sgd_grid = [{"alpha": a} for a in [0.0001, 0.001, 0.01]]

    search_space = []
    for p in rf_grid:
        search_space.append(("RandomForest", p))
    for p in xgb_grid:
        search_space.append(("XGBoost", p))
    for p in sgd_grid:
        search_space.append(("SGDRegressor", p))

    # -------- launch every combo in parallel with concurrency tag -----------
    futures = []
    for model_type, params in search_space:
        f = run_model_combo.submit(
            model_type, params, total_rows, batches, tags=["model_run"]
        )
        futures.append(f)

    # optional: wait for all sub‑flows to finish
    results = [f.result() for f in futures]
    return results


if __name__ == "__main__":
    ml_regression_pipeline_parallel()

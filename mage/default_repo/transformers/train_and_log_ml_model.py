if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test



import mlflow
import mlflow.sklearn
from sklearn.linear_model import LinearRegression ,SGDRegressor
from sklearn.model_selection import train_test_split
from datetime import datetime
from mlflow.tracking import MlflowClient
import gc
import psutil
import math
import os
from pathlib import Path
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor       # NEW
from xgboost import XGBRegressor                         # NEW
from sklearn.metrics import mean_squared_error  



def _log_mem(tag: str = ""):
    process = psutil.Process(os.getpid())
    rss_mb = process.memory_info().rss / 1024 ** 2
    print(f"[{tag}] RSS: {rss_mb:.1f} MB")


# ------------------------- helper to train batch -------------------------
def train_random_forest_in_batches(model, X_batch, y_batch,
                                   trees_per_batch: int = 50):
    """
    If model is brand‑new:
        * warm_start=True so subsequent fits add trees
        * n_estimators = trees_per_batch
    If model already exists:
        * bump n_estimators by trees_per_batch
        * call fit again (sklearn adds new trees only)
    """
    if not hasattr(model, "n_estimators"):          # brand‑new model
        model.set_params(warm_start=True,
                         n_estimators=trees_per_batch)
    else:                                           # existing model
        model.set_params(
            warm_start=True,
            n_estimators=model.n_estimators + trees_per_batch
        )
    model.fit(X_batch, y_batch)                     # grows the forest
    return model

# ------------------------- helper to train batch -------------------------
# === helper to train an XGBRegressor in batches ===
def train_xgboost_in_batches(
    model,
    X_batch,
    y_batch,
    rounds_per_batch: int = 50,
):
    """
    Incrementally trains an XGBRegressor.

    If ``model`` is None, create a fresh model with the requested
    number of boosting rounds, then fit once.

    Otherwise, increase ``n_estimators`` by ``rounds_per_batch``
    and fit again while passing the existing booster so the new
    trees extend the previous ones.
    """
    if model is None:
        model = XGBRegressor(
            n_estimators=rounds_per_batch,
            random_state=42,
            use_label_encoder=False,
            eval_metric="rmse",
        )
        model.fit(X_batch, y_batch)
        return model

    current_estimators = model.get_params().get("n_estimators") or 0
    new_estimators = current_estimators + rounds_per_batch
    model.set_params(n_estimators=new_estimators)

    booster = getattr(model, "_Booster", None)  # None on first call
    model.fit(X_batch, y_batch, xgb_model=booster)
    return model

    
@transformer
def transform(train_dict, *args, **kwargs):
    """
    Template code for a transformer block.

    Add more parameters to this function if this block has multiple parent blocks.
    There should be one parameter for each output variable from each parent block.

    Args:
        data: The output from the upstream parent block
        args: The output from any additional upstream blocks (if applicable)

    Returns:
        Anything (e.g. data frame, dictionary, array, int, str, etc.)
    """

    run_uuid = kwargs.get("run_uuid") or "dummy"
    is_last_batch = kwargs.get("is_last_batch") or False
    model_type = kwargs.get("model_type") or "SGDRegressor"
    params = kwargs.get("params") or {"alpha": 0.001}
    
    MODEL_DIR = Path("/home/src/models/experiment")
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    model_path = MODEL_DIR / f"{run_uuid}_{model_type}.pkl"        # FIXED

    


    # Specify your transformation logic here
    X_train = train_dict['X_train']
    y_train = train_dict['y_train']
    X_test = train_dict['X_test']
    y_test = train_dict['y_test']

    mlflow.set_tracking_uri("http://mlflow:5000") 
    experiment_name = f"ml-{model_type.lower()}"
    
    existing_experiment = mlflow.get_experiment_by_name(experiment_name)
    if existing_experiment is None:
        mlflow.create_experiment(experiment_name)

     # Get or create the experiment and capture its id
    exp = mlflow.get_experiment_by_name(experiment_name)
    if exp is None:
        exp_id = mlflow.create_experiment(experiment_name)
    else:
        exp_id = exp.experiment_id

    # Now build the client for this URI
    client = MlflowClient()

    # Remove prior runs that share the same tag
    old_runs = client.search_runs(
        experiment_ids=[exp_id],
        filter_string=f"tags.run_uuid = '{run_uuid}'"
    )
    for r in old_runs:
        client.delete_run(r.info.run_id)

    # Start a fresh run
    mlflow.set_experiment(experiment_name)
    mlflow.sklearn.autolog()

    if model_path.exists():
        model = joblib.load(model_path)
    else:
        if model_type == "SGDRegressor":
            model = SGDRegressor(random_state=42, **params)
        elif model_type == "RandomForest":
            model = RandomForestRegressor(random_state=42, **params)
        elif model_type == "XGBoost":
            model = XGBRegressor(random_state=42, **params, use_label_encoder=False, eval_metric="rmse")
        else:
            raise ValueError(f"Unknown model_type: {model_type}")
    
    # Add custom tags
    with mlflow.start_run() as run:

        if is_last_batch:
            model.fit(X_train, y_train)
            y_train_pred=model.predict(X_train)
            y_test_pred=model.predict(X_test)
        else:    
            if model_type == "RandomForest":
                model = train_random_forest_in_batches(model, X_train, y_train, trees_per_batch=50)
            elif model_type == "XGBoost":
                model = train_xgboost_in_batches(model, X_train, y_train, rounds_per_batch=50)
            
            else:
                model.partial_fit(X_train, y_train)   
            y_train_pred=model.predict(X_train)
            y_test_pred=model.predict(X_test)     
        # Save model for the next pass
       
        joblib.dump(model, model_path) 

        rmse = math.sqrt(mean_squared_error(y_test, y_test_pred))   # ADDED
        
        mlflow.log_metric("rmse", rmse)                             # ADDED

        mlflow.set_tag("run_uuid", run_uuid)
        mlflow.set_tag("run_datetime", datetime.now().isoformat()) 
        mlflow.set_tag("model_type", model_type)
        mlflow.set_tag("params", str(params))

        train_dict['y_train_pred']=pd.DataFrame(y_train_pred)
        train_dict['y_test_pred']=pd.DataFrame(y_test_pred)



    ############################################################################
    # After the final batch, choose the best run and register it
    ############################################################################
    if is_last_batch:
        # 1. Fetch all FINISHED runs for this experiment
        finished_runs = client.search_runs(
            experiment_ids=[exp_id],
            filter_string="attributes.status = 'FINISHED'"
        )

        # 2. Group by run_uuid tag and track best run per group
        best_runs_per_uuid = {}
        for run in finished_runs:
            run_tags = run.data.tags
            run_uuid = run_tags.get("run_uuid")
            if not run_uuid:
                continue
            rmse = run.data.metrics.get("rmse", float("inf"))
            if run_uuid not in best_runs_per_uuid or rmse < best_runs_per_uuid[run_uuid].data.metrics.get("rmse", float("inf")):
                best_runs_per_uuid[run_uuid] = run

        # 3. Now pick the best RMSE from the grouped bests
        if not best_runs_per_uuid:
            print("No valid runs with rmse and run_uuid found.")
            return

        best_run = min(best_runs_per_uuid.values(), key=lambda r: r.data.metrics.get("rmse", float("inf")))
        best_rmse = best_run.data.metrics["rmse"]

        model_uri     = f"runs:/{best_run.info.run_id}/model"
        registry_name = f"{model_type}_baseline"

        # 4. Create registry if needed
        try:
            client.get_registered_model(registry_name)
        except Exception:
            client.create_registered_model(registry_name)

        # 5. Compare with existing Production version
        current_versions = client.get_latest_versions(registry_name, stages=["Production"])
        if current_versions:
            current_rmse = float(current_versions[0].tags.get("rmse", float("inf")))
        else:
            current_rmse = float("inf")

        # 6. Register only if better
        if best_rmse < current_rmse:
            mv = client.create_model_version(
                name=registry_name,
                source=model_uri,
                run_id=best_run.info.run_id
            )

            client.set_model_version_tag(
                name=registry_name,
                version=mv.version,
                key="rmse",
                value=str(best_rmse)
            )

            client.transition_model_version_stage(
                name=registry_name,
                version=mv.version,
                stage="Production",
                archive_existing_versions=True
            )
            print(f"Registered {registry_name} version {mv.version} with RMSE {best_rmse:.4f}")
        else:
            print(f"Skipped registration. Existing Production model has better RMSE: {current_rmse:.4f}")

    #del train_dict
    #gc.collect()
    #_log_mem("after gc")


    return train_dict
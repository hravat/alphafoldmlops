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
import gc
import psutil
import os
from pathlib import Path
import joblib

def _log_mem(tag: str = ""):
    process = psutil.Process(os.getpid())
    rss_mb = process.memory_info().rss / 1024 ** 2
    print(f"[{tag}] RSS: {rss_mb:.1f} MB")


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

    MODEL_PATH = Path("/home/src/models/regerssion/sgd_reg.pkl")

    if MODEL_PATH.exists():
        model = joblib.load(MODEL_PATH)
    else:
        model = SGDRegressor(random_state=42)


    # Specify your transformation logic here
    X_train = train_dict['X_train']
    y_train = train_dict['y_train']
    run_uuid=kwargs['run_uuid']
    is_last_batch=kwargs['is_last_batch']

    mlflow.set_tracking_uri("http://mlflow:5000") 

    experiment_name='ml-limear-regression'
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
    
    # Add custom tags
    with mlflow.start_run() as run:

        if is_last_batch:
            model.fit(X_train, y_train)
        else:    
            model.partial_fit(X_train, y_train)        
        # Save model for the next pass
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, MODEL_PATH)
        
        mlflow.set_tag("run_uuid", run_uuid)
        mlflow.set_tag("run_datetime", datetime.now().isoformat()) 



    del train_dict
    gc.collect()
    _log_mem("after gc")


    return None

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test

import mlflow
import mlflow.sklearn
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from datetime import datetime
from mlflow.tracking import MlflowClient

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
    # Specify your transformation logic here
    X_train = train_dict['X_train']
    y_train = train_dict['y_train']
    run_uuid=kwargs['run_uuid']

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

        model = LinearRegression()
        model.fit(X_train, y_train)        
        mlflow.set_tag("run_uuid", run_uuid)
        mlflow.set_tag("run_datetime", datetime.now().isoformat()) 

    return train_dict


@test
def test_output(output, *args) -> None:
    """
    Template code for testing the output of the block.
    """
    assert output is not None, 'The output is undefined'

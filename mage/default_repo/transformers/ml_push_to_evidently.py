if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test


from evidently.ui.workspace import RemoteWorkspace
from evidently.presets import DataDriftPreset, RegressionPreset
from evidently import Dataset, DataDefinition, Regression ,Report  # new imports

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

    # ------------------------------------------------------------------
    # 0.  Where is the Evidently UI service?
    #     Inside Docker compose the mage container can reach it with
    #     http://evidently:8000      (service name "evidently")
    # ------------------------------------------------------------------
    
    workspace = "http://evidently:8000"
    ws = RemoteWorkspace(workspace)



    PROJECT_NAME = "Alphafold Linear Regression"

    projects = ws.list_projects()
    project = next((p for p in projects if p.name == PROJECT_NAME), None)

    if project:
        print(f"Project '{PROJECT_NAME}' exists with ID: {project.id}")
    else:
        print(f"Project '{PROJECT_NAME}' does not exist, creating it now...")
        project=ws.create_project(PROJECT_NAME)
        project.description="Monitoring basic regression metrics for Alphafold pipeline"
        project.save()
        print(f"Created project '{PROJECT_NAME}'")



    reg_defintion = DataDefinition(
    regression=[Regression(target="standard_value", prediction="y_pred")]
    )

    report = Report([
    RegressionPreset(),
    DataDriftPreset()
    ],
    include_tests=True)

    reference_df = train_dict["X_train"]   # must contain y_true and y_pred
    current_df   = train_dict["X_test"]
    y_train_pred = train_dict["y_train_pred"]
    y_test_pred = train_dict["y_test_pred"]
    y_train=train_dict['y_train']
    y_test=train_dict['y_test']

    reference_df['y_pred']=y_train_pred
    current_df['y_pred']=y_test_pred
    reference_df['standard_value']=y_train
    current_df['standard_value']=y_train

    reference_ds = Dataset.from_pandas(reference_df, data_definition=reg_defintion)
    current_ds   = Dataset.from_pandas(current_df,   data_definition=reg_defintion)

    my_eval = report.run(reference_ds, current_ds)

    ws.add_run(project.id, my_eval)
    
    my_eval_dict = my_eval.dict()

    return my_eval_dict



@test
def test_output(output, *args) -> None:
    """
    Template code for testing the output of the block.
    """
    assert output is not None, 'The output is undefined'

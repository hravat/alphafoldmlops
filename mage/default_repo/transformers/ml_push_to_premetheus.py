if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test

from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

@transformer
def transform(my_eval_dict, *args, **kwargs):
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

    
    name_map = {
    "MAPE_mean": "alf_mape_mean",
    "MAPE_std":  "alf_mape_std",
    "MAE_mean":  "alf_mae_mean",
    "MAE_std":   "alf_mae_std",
    "RMSE":      "alf_rmse",
    "R2Score":   "alf_r2",
    "AbsMaxError": "alf_abs_max_err",
    "DriftedColumnsCount_count": "alf_drift_cols_cnt",
    "DriftedColumnsCount_share": "alf_drift_cols_share",
    "ValueDrift(column=mw_freebase)": "alf_vd_mw_freebase",
    "ValueDrift(column=alogp)":       "alf_vd_alogp",
    "ValueDrift(column=hba)":         "alf_vd_hba",
    "ValueDrift(column=hbd)":         "alf_vd_hbd",
    "ValueDrift(column=y_pred)":      "alf_vd_y_pred",
    "ValueDrift(column=standard_value)": "alf_vd_std_val",
    }
    
    registry = CollectorRegistry()

    for item in my_eval_dict['metrics']:
        metric_id = item["metric_id"]
        value = item["value"]

        # MAPE
        if metric_id.startswith("MAPE"):
            Gauge("alf_mape_mean", "alf_mape_mean", registry=registry).set(value["mean"])
            Gauge("alf_mape_std", "alf_mape_std", registry=registry).set(value["std"])

        # MAE
        elif metric_id.startswith("MAE"):
            Gauge("alf_mae_mean", "alf_mae_mean", registry=registry).set(value["mean"])
            Gauge("alf_mae_std", "alf_mae_std", registry=registry).set(value["std"])

        # RMSE
        elif metric_id.startswith("RMSE"):
            Gauge("alf_rmse", "alf_rmse", registry=registry).set(value)

        # R2
        elif metric_id.startswith("R2Score"):
            Gauge("alf_r2", "alf_r2", registry=registry).set(value)

        # AbsMaxError
        elif metric_id.startswith("AbsMaxError"):
            Gauge("alf_abs_max_err", "alf_abs_max_err", registry=registry).set(value)

        # DriftedColumnsCount
        elif metric_id.startswith("DriftedColumnsCount"):
            Gauge("alf_drift_cols_cnt", "alf_drift_cols_cnt", registry=registry).set(value["count"])
            Gauge("alf_drift_cols_share", "alf_drift_cols_share", registry=registry).set(value["share"])

        # ValueDrift columns
        elif metric_id.startswith("ValueDrift(column="):
            col_name = metric_id.split("=", 1)[1].rstrip(")")
            metric_name = f"alf_vd_{col_name}"
            Gauge(metric_name, metric_name, registry=registry).set(value)

    push_to_gateway("http://pushgateway:9091", job="alf_job", registry=registry)




    #registry = CollectorRegistry()
#
    ## Define some dummy gauges
    #g_mae = Gauge("dummy_mae", "Dummy MAE metric", registry=registry)
    #g_r2 = Gauge("dummy_r2_score", "Dummy R2 score metric", registry=registry)
#
    ## Set dummy values
    #g_mae.set(0.123)
    #g_r2.set(0.987)
#
# Pu#sh to your Pushgateway (change URL if needed)
    #push_to_gateway("http://pushgateway:9091", job="dummy_job", registry=registry)

    print("Dummy metrics pushed successfully")

    return 'Test'


@test
def test_output(output, *args) -> None:
    """
    Template code for testing the output of the block.
    """
    assert output is not None, 'The output is undefined'

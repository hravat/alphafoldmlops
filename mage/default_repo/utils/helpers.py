"""Utility helpers for incremental model training.
These functions are imported by the Mage transformer block.
"""
from __future__ import annotations

import os
import psutil
from xgboost import XGBRegressor
from sklearn.ensemble import RandomForestRegressor


def log_mem(tag: str = "") -> None:
    """Print the resident set size for the current process in MB."""
    process = psutil.Process(os.getpid())
    rss_mb = process.memory_info().rss / 1024 ** 2
    print(f"[{tag}] RSS: {rss_mb:.1f} MB")


# ------------------------- Random Forest ---------------------------------

def train_random_forest_in_batches(
    model: RandomForestRegressor,
    X_batch,
    y_batch,
    trees_per_batch: int = 50,
):
    """Grow a RandomForestRegressor in chunks of *trees_per_batch* trees.

    If *model* is brand new, *warm_start* is enabled and *n_estimators*
    is set to *trees_per_batch*.
    If *model* already has trees, *n_estimators* is increased by
    *trees_per_batch* and *fit* is called again. Scikit‑learn appends the new
    trees to the existing ensemble when *warm_start* is True.
    """
    if not hasattr(model, "n_estimators"):
        # brand new model
        model.set_params(warm_start=True, n_estimators=trees_per_batch)
    else:
        # grow the existing forest
        model.set_params(
            warm_start=True,
            n_estimators=model.n_estimators + trees_per_batch,
        )

    model.fit(X_batch, y_batch)
    return model


# --------------------------- XGBoost -------------------------------------

def train_xgboost_in_batches(
    model: XGBRegressor | None,
    X_batch,
    y_batch,
    rounds_per_batch: int = 50,
):
    """Incrementally train an XGBRegressor.

    If *model* is None, a fresh booster is created with
    *rounds_per_batch* trees and fitted once.

    If *model* already exists, *n_estimators* is increased by
    *rounds_per_batch* and *fit* is called again, passing the existing
    booster so the new trees extend the previous ones.
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

    booster = getattr(model, "_Booster", None)
    model.fit(X_batch, y_batch, xgb_model=booster)
    return model

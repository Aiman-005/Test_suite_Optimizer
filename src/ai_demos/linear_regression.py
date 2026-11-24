"""
Supervised learning: predict a test's future duration with linear regression.

Task:     regression. One sample per test.
Features: statistics of the test's first five timing runs
          (historical_mean, historical_min, historical_max, historical_std).
Target:   the mean of the same test's runs 6-10 ("future duration").

Evaluation: 5-fold cross-validation over all tests of a project, so every
test is predicted once by a model that never saw it. The model is
compared with two baselines that need no training:
- historical mean: predict the mean of runs 1-5
- Kalman filter:   the project's own KalmanDurationEstimator on runs 1-5
Metrics: MAE and RMSE (milliseconds) and R^2.

    python -m src.ai_demos.linear_regression
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_val_predict

from src.core.kalman_filter import KalmanDurationEstimator

PROJECTS = ["tinydb", "toolz", "boltons"]
FEATURES = ["historical_mean", "historical_min", "historical_max", "historical_std"]
DATA_DIR = Path("data/processed")
OUTPUT_DIR = Path("results/ml")


def prepare_dataset(project):
    """Build one row per test: features from runs 1-5, target from runs 6-10."""

    data = pd.read_csv(DATA_DIR / f"{project}_timing_runs.csv")
    data = data[data["status"] == "passed"]

    runs = data.pivot_table(
        index="node_id", columns="run_number", values="duration_seconds"
    ).dropna()

    history = runs[[1, 2, 3, 4, 5]]

    dataset = pd.DataFrame({
        "node_id": runs.index,
        "historical_mean": history.mean(axis=1).values,
        "historical_min": history.min(axis=1).values,
        "historical_max": history.max(axis=1).values,
        "historical_std": history.std(axis=1).values,
        "kalman_estimate": [
            KalmanDurationEstimator().estimate_duration(list(values))
            for values in history.values
        ],
        "actual_duration": runs[[6, 7, 8, 9, 10]].mean(axis=1).values,
    })

    return dataset


def score(project, model_name, actual, predicted):
    return {
        "project": project,
        "model": model_name,
        "samples": len(actual),
        "mae_ms": mean_absolute_error(actual, predicted) * 1000,
        "rmse_ms": np.sqrt(mean_squared_error(actual, predicted)) * 1000,
        "r2": r2_score(actual, predicted),
    }


def run_linear_regression():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    metrics, predictions, coefficients = [], [], []

    for project in PROJECTS:
        dataset = prepare_dataset(project)
        X = dataset[FEATURES]
        y = dataset["actual_duration"]

        folds = KFold(n_splits=5, shuffle=True, random_state=42)
        predicted = cross_val_predict(LinearRegression(), X, y, cv=folds)

        metrics += [
            score(project, "Linear regression (5-fold CV)", y, predicted),
            score(project, "Baseline: historical mean", y, dataset["historical_mean"]),
            score(project, "Baseline: Kalman filter", y, dataset["kalman_estimate"]),
        ]

        final_model = LinearRegression().fit(X, y)
        coefficients.append({
            "project": project,
            "intercept_ms": final_model.intercept_ * 1000,
            **{f"coef_{name}": value for name, value in zip(FEATURES, final_model.coef_)},
        })

        for node_id, actual, pred, mean in zip(
            dataset["node_id"], y, predicted, dataset["historical_mean"]
        ):
            predictions.append({
                "project": project,
                "node_id": node_id,
                "actual_duration": actual,
                "predicted_duration": pred,
                "historical_mean": mean,
                "absolute_error": abs(actual - pred),
            })

    metrics = pd.DataFrame(metrics)
    metrics.to_csv(OUTPUT_DIR / "linear_regression_metrics.csv", index=False)
    pd.DataFrame(predictions).to_csv(
        OUTPUT_DIR / "linear_regression_predictions.csv", index=False
    )
    pd.DataFrame(coefficients).to_csv(
        OUTPUT_DIR / "linear_regression_coefficients.csv", index=False
    )

    print(metrics.round(4).to_string(index=False))
    print("\nCoefficients of the model fitted on all tests:")
    print(pd.DataFrame(coefficients).round(4).to_string(index=False))
    print("\nResults saved in:", OUTPUT_DIR)


if __name__ == "__main__":
    run_linear_regression()

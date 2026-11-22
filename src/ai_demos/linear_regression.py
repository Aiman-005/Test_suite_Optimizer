
import numpy as np
import pandas as pd
from pathlib import Path

from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


PROJECTS = ["tinydb", "toolz", "boltons"]

FEATURES = [
    "historical_mean",
    "historical_min",
    "historical_max",
    "historical_std"
]


def prepare_dataset(project):
    """Build historical features and future execution-time targets."""

    path = Path(f"data/processed/{project}_timing_runs.csv")
    data = pd.read_csv(path)

    # Exclude skipped or failed measurements.
    data = data[data["status"] == "passed"].copy()

    # Use runs 1-5 as historical measurements.
    historical = data[data["run_number"] <= 5]

    features = (
        historical.groupby("node_id")["duration_seconds"]
        .agg(["mean", "min", "max", "std"])
        .reset_index()
    )

    features.columns = [
        "node_id",
        "historical_mean",
        "historical_min",
        "historical_max",
        "historical_std"
    ]

    # Use runs 6-10 as the actual future duration.
    future = (
        data[data["run_number"] >= 6]
        .groupby("node_id")["duration_seconds"]
        .mean()
        .reset_index()
    )

    future.columns = ["node_id", "actual_duration"]

    # Match historical features with future targets.
    dataset = features.merge(future, on="node_id", how="inner")

    return dataset.dropna()


def run_linear_regression():
    """Train and evaluate a duration prediction model for each project."""

    output_dir = Path("results/ml")
    output_dir.mkdir(parents=True, exist_ok=True)

    all_predictions = []
    all_metrics = []

    for project in PROJECTS:
        dataset = prepare_dataset(project)

        X = dataset[FEATURES]
        y = dataset["actual_duration"]

        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=0.2,
            random_state=42
        )

        model = LinearRegression()
        model.fit(X_train, y_train)

        predictions = model.predict(X_test)

        mae = mean_absolute_error(y_test, predictions)
        rmse = np.sqrt(mean_squared_error(y_test, predictions))
        r2 = r2_score(y_test, predictions)

        print(f"\n{project.upper()} LINEAR REGRESSION")
        print("-" * 40)
        print(f"Total samples: {len(dataset)}")
        print(f"Training samples: {len(X_train)}")
        print(f"Testing samples: {len(X_test)}")
        print(f"MAE:  {mae:.8f} seconds")
        print(f"RMSE: {rmse:.8f} seconds")
        print(f"R²:   {r2:.4f}")

        for node_id, actual, predicted in zip(
            dataset.loc[X_test.index, "node_id"],
            y_test,
            predictions
        ):
            all_predictions.append({
                "project": project,
                "node_id": node_id,
                "actual_duration": actual,
                "predicted_duration": predicted,
                "absolute_error": abs(actual - predicted)
            })

        all_metrics.append({
            "project": project,
            "samples": len(dataset),
            "training_samples": len(X_train),
            "testing_samples": len(X_test),
            "mae": mae,
            "rmse": rmse,
            "r2": r2
        })

    pd.DataFrame(all_metrics).to_csv(
        output_dir / "linear_regression_metrics.csv",
        index=False
    )

    pd.DataFrame(all_predictions).to_csv(
        output_dir / "linear_regression_predictions.csv",
        index=False
    )

    print("\nResults saved in:", output_dir)


if __name__ == "__main__":
    run_linear_regression()

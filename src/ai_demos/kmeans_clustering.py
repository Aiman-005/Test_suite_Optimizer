
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler


def run_project_experiment(project):
    timing_path = Path(
        f"data/processed/{project}_kalman_estimates.csv"
    )
    coverage_path = Path(
        f"data/processed/{project}_coverage_matrix.csv"
    )

    output_dir = Path("results/ml")
    output_dir.mkdir(parents=True, exist_ok=True)

    timing = pd.read_csv(timing_path)
    coverage = pd.read_csv(coverage_path)

    # Normalize column names across projects.
    timing = timing.rename(columns={
    "node_id": "test_node_id",
    "estimated_duration": "kalman_estimate_seconds"
    })

    # Count unique covered lines per test and source file.
    coverage_by_file = (
        coverage.groupby(["test_node_id", "source_file"])["covered_lines"]
        .apply(
            lambda values: len({
                line.strip()
                for value in values.dropna()
                for line in str(value).split(";")
                if line.strip()
            })
        )
        .reset_index(name="covered_line_count")
    )

    # Calculate total covered lines per test.
    coverage_summary = (
        coverage_by_file.groupby("test_node_id")["covered_line_count"]
        .sum()
        .reset_index()
    )

    # Join duration and coverage data.
    data = timing.merge(
        coverage_summary,
        on="test_node_id",
        how="inner"
    )

    data = data.dropna(
        subset=["kalman_estimate_seconds", "covered_line_count"]
    )

    features = data[
        ["kalman_estimate_seconds", "covered_line_count"]
    ]

    if len(data) < 7:
        print(f"Not enough tests for {project}. Skipping.")
        return

    # Scale the features.
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(features)

    # Evaluate different cluster counts.
    cluster_results = []

    for k in range(2, 7):
        model = KMeans(
            n_clusters=k,
            random_state=42,
            n_init=10
        )

        labels = model.fit_predict(scaled_features)

        if len(set(labels)) < 2:
            continue

        score = silhouette_score(scaled_features, labels)

        cluster_results.append({
            "n_clusters": k,
            "inertia": model.inertia_,
            "silhouette_score": score
        })

    metrics = pd.DataFrame(cluster_results)

    best_k = int(
        metrics.loc[
            metrics["silhouette_score"].idxmax(),
            "n_clusters"
        ]
    )

    # Fit final model.
    final_model = KMeans(
        n_clusters=best_k,
        random_state=42,
        n_init=10
    )

    data["cluster"] = final_model.fit_predict(scaled_features)

    # Save assignments.
    assignments = data[
        [
            "test_node_id",
            "kalman_estimate_seconds",
            "covered_line_count",
            "cluster"
        ]
    ]

    assignments.to_csv(
        output_dir / f"{project}_kmeans_clusters.csv",
        index=False
    )

    metrics.to_csv(
        output_dir / f"{project}_kmeans_metrics.csv",
        index=False
    )

    # Generate cluster summary.
    summary = (
        data.groupby("cluster")
        .agg(
            test_count=("test_node_id", "count"),
            average_duration=("kalman_estimate_seconds", "mean"),
            average_covered_lines=("covered_line_count", "mean")
        )
        .reset_index()
    )

    summary.to_csv(
        output_dir / f"{project}_kmeans_cluster_summary.csv",
        index=False
    )

    # Generate scatter plot.
    plt.figure(figsize=(10, 6))

    for cluster_id in sorted(data["cluster"].unique()):
        cluster_data = data[data["cluster"] == cluster_id]

        plt.scatter(
            cluster_data["kalman_estimate_seconds"],
            cluster_data["covered_line_count"],
            label=f"Cluster {cluster_id}"
        )

    plt.xlabel("Estimated Execution Duration (seconds)")
    plt.ylabel("Number of Covered Source Lines")
    plt.title(f"{project.title()} Test Clusters (K-Means, k={best_k})")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    plt.savefig(
        output_dir / f"{project}_kmeans_clusters.png",
        dpi=300
    )

    plt.close()

    print(f"\n{'=' * 45}")
    print(f"PROJECT: {project.upper()}")
    print(f"{'=' * 45}")
    print("Tests included:", len(data))
    print("Selected clusters:", best_k)

    print("\nEvaluation:")
    print(metrics.to_string(index=False))

    print("\nCluster summary:")
    print(summary.to_string(index=False))


def main():
    for project in ["tinydb", "toolz", "boltons"]:
        run_project_experiment(project)


if __name__ == "__main__":
    main()

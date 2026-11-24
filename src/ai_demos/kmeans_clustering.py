"""
K-Means clustering of tests by cost and coverage (unsupervised learning).

Features per test:
- log10 of the Kalman-estimated duration (seconds)
- log(1 + number of unique covered source lines)
Both are standardised. Durations span four orders of magnitude, so
without the log a handful of slow tests dominate the distance and
K-Means only separates those outliers from everything else.

k is searched from 2 to 6 and chosen by the highest silhouette score.

    python -m src.ai_demos.kmeans_clustering
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

PROJECTS = ["tinydb", "toolz", "boltons"]
DATA_DIR = Path("data/processed")
OUTPUT_DIR = Path("results/ml")


def load_features(project):
    timing = pd.read_csv(DATA_DIR / f"{project}_kalman_estimates.csv")
    coverage = pd.read_csv(DATA_DIR / f"{project}_coverage_matrix.csv")

    # Count unique lines per file, then sum across files.
    per_file = (
        coverage.groupby(["test_node_id", "source_file"])["covered_lines"]
        .apply(lambda values: len({
            line.strip()
            for value in values.dropna()
            for line in str(value).split(";")
            if line.strip()
        }))
        .groupby("test_node_id").sum()
        .rename("covered_line_count")
    )
    data = timing.merge(
        per_file, left_on="test_node_id", right_index=True, how="inner"
    )

    return data[["test_node_id", "kalman_estimate_seconds", "covered_line_count"]]


def run_project_experiment(project):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data = load_features(project)

    if len(data) < 7:
        print(f"Not enough tests for {project}. Skipping.")
        return None

    features = np.column_stack([
        np.log10(data["kalman_estimate_seconds"]),
        np.log1p(data["covered_line_count"])
    ])
    scaled = StandardScaler().fit_transform(features)

    results = []
    for k in range(2, 7):
        model = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = model.fit_predict(scaled)
        results.append({
            "n_clusters": k,
            "inertia": model.inertia_,
            "silhouette_score": silhouette_score(scaled, labels)
        })

    metrics = pd.DataFrame(results)
    best_k = int(metrics.loc[metrics["silhouette_score"].idxmax(), "n_clusters"])

    final_model = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    data = data.copy()
    data["cluster"] = final_model.fit_predict(scaled)

    # Number clusters from fastest (0) to slowest so labels are stable.
    order = (
        data.groupby("cluster")["kalman_estimate_seconds"].median()
        .sort_values().index.tolist()
    )
    data["cluster"] = data["cluster"].map({old: new for new, old in enumerate(order)})

    data.to_csv(OUTPUT_DIR / f"{project}_kmeans_clusters.csv", index=False)
    metrics.to_csv(OUTPUT_DIR / f"{project}_kmeans_metrics.csv", index=False)

    summary = (
        data.groupby("cluster")
        .agg(
            test_count=("test_node_id", "count"),
            average_duration=("kalman_estimate_seconds", "mean"),
            median_duration=("kalman_estimate_seconds", "median"),
            average_covered_lines=("covered_line_count", "mean")
        )
        .reset_index()
    )
    summary["lines_per_millisecond"] = (
        summary["average_covered_lines"] / (summary["median_duration"] * 1000)
    )
    summary.to_csv(OUTPUT_DIR / f"{project}_kmeans_cluster_summary.csv", index=False)

    plt.figure(figsize=(10, 6))
    for cluster_id in sorted(data["cluster"].unique()):
        part = data[data["cluster"] == cluster_id]
        plt.scatter(
            part["kalman_estimate_seconds"], part["covered_line_count"],
            label=f"Cluster {cluster_id}", alpha=0.7
        )
    plt.xscale("log")
    plt.xlabel("Estimated execution duration (seconds, log scale)")
    plt.ylabel("Covered source lines")
    plt.title(f"{project.title()} test clusters (K-Means, k={best_k})")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / f"{project}_kmeans_clusters.png", dpi=200)
    plt.close()

    smallest = summary.loc[summary["test_count"].idxmin()]
    best_sil = float(metrics["silhouette_score"].max())

    print(f"\n{project.upper()}: {len(data)} tests, k={best_k}, silhouette={best_sil:.3f}")
    print(summary.to_string(index=False))

    return {
        "project": project,
        "total_tests_clustered": len(data),
        "selected_clusters": best_k,
        "silhouette_score": best_sil,
        "smallest_cluster": int(smallest["cluster"]),
        "smallest_cluster_tests": int(smallest["test_count"]),
        "smallest_cluster_avg_duration": float(smallest["average_duration"]),
        "smallest_cluster_avg_covered_lines": float(smallest["average_covered_lines"])
    }


def main():
    rows = [r for r in (run_project_experiment(p) for p in PROJECTS) if r]
    summary = pd.DataFrame(rows)
    summary.to_csv(OUTPUT_DIR / "kmeans_cross_project_summary.csv", index=False)

    for column, filename, label in [
        ("silhouette_score", "kmeans_silhouette_comparison.png", "Best silhouette score"),
        ("smallest_cluster_tests", "kmeans_smallest_cluster_comparison.png", "Tests in smallest cluster"),
    ]:
        plt.figure(figsize=(7, 4))
        plt.bar(summary["project"], summary[column], color="#4C78A8")
        plt.ylabel(label)
        plt.title(label + " by project")
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / filename, dpi=200)
        plt.close()

    print("\nSaved results to", OUTPUT_DIR)


if __name__ == "__main__":
    main()

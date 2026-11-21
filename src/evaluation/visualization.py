import csv
from pathlib import Path

import matplotlib.pyplot as plt


def load_benchmark_data(csv_path):
    """Load combined benchmark results from CSV."""
    with Path(csv_path).open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def create_comparison_charts(
    csv_path="results/combined_benchmark.csv",
    output_dir="results/charts"
):
    """Generate coverage, selected-test, and optimizer-runtime charts."""

    data = load_benchmark_data(csv_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    projects = list(dict.fromkeys(row["project"] for row in data))
    optimizers = list(dict.fromkeys(row["optimizer"] for row in data))

    def grouped_chart(metric, title, ylabel, filename, skip_missing=False):
        x_positions = list(range(len(projects)))
        bar_width = 0.8 / len(optimizers)

        plt.figure(figsize=(11, 6))

        for index, optimizer in enumerate(optimizers):
            values = []
            positions = []

            for project_index, project in enumerate(projects):
                matches = [
                    row for row in data
                    if row["project"] == project
                    and row["optimizer"] == optimizer
                ]

                if not matches:
                    continue

                value = matches[0][metric]

                if skip_missing and not value.strip():
                    continue

                if not value.strip():
                    continue

                values.append(float(value))
                positions.append(
                    x_positions[project_index]
                    - 0.4
                    + bar_width / 2
                    + index * bar_width
                )

            plt.bar(
                positions,
                values,
                width=bar_width,
                label=optimizer
            )

        plt.title(title)
        plt.xlabel("Project")
        plt.ylabel(ylabel)
        plt.xticks(x_positions, projects)
        plt.legend()
        plt.tight_layout()
        plt.savefig(output_dir / filename, dpi=300)
        plt.close()

    grouped_chart(
        "coverage_percentage",
        "Code Coverage by Optimizer and Project",
        "Coverage (%)",
        "coverage_comparison.png"
    )

    grouped_chart(
        "selected_tests",
        "Number of Selected Tests by Optimizer and Project",
        "Number of Tests",
        "selected_tests_comparison.png",
        skip_missing=True
    )

    grouped_chart(
        "optimizer_runtime_seconds",
        "Optimizer Runtime by Project",
        "Runtime (seconds)",
        "optimizer_runtime_comparison.png"
    )

    print("Charts generated successfully:")
    for filename in [
        "coverage_comparison.png",
        "selected_tests_comparison.png",
        "optimizer_runtime_comparison.png"
    ]:
        print(output_dir / filename)


if __name__ == "__main__":
    create_comparison_charts()

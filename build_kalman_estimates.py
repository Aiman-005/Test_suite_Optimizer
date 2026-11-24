"""
Turn repeated timing runs into Kalman-filtered duration estimates.

    python build_kalman_estimates.py            # all three projects
    python build_kalman_estimates.py tinydb     # one project

Reads  data/processed/<name>_timing_runs.csv
Writes data/processed/<name>_kalman_estimates.csv with the columns
    test_node_id, raw_mean_seconds, kalman_estimate_seconds, measurements
(the same columns for every project). Only passed runs are used.
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

from src.core.kalman_filter import KalmanDurationEstimator

DATA_DIR = Path("data/processed")
PROJECTS = ["tinydb", "toolz", "boltons"]
FIELDS = [
    "test_node_id",
    "raw_mean_seconds",
    "kalman_estimate_seconds",
    "measurements"
]


def build_estimates(name):
    timing_path = DATA_DIR / f"{name}_timing_runs.csv"
    output_path = DATA_DIR / f"{name}_kalman_estimates.csv"

    measurements = defaultdict(list)

    with timing_path.open(newline="", encoding="utf-8") as file:
        rows = sorted(csv.DictReader(file), key=lambda r: int(r["run_number"]))

    for row in rows:
        duration = float(row["duration_seconds"])

        if row["status"] == "passed" and duration > 0:
            measurements[row["node_id"]].append(duration)

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()

        for node_id, values in measurements.items():
            estimate = KalmanDurationEstimator().estimate_duration(values)

            writer.writerow({
                "test_node_id": node_id,
                "raw_mean_seconds": sum(values) / len(values),
                "kalman_estimate_seconds": estimate,
                "measurements": len(values)
            })

    print(f"{name}: {len(measurements)} tests -> {output_path}")


if __name__ == "__main__":
    for project in sys.argv[1:] or PROJECTS:
        build_estimates(project)

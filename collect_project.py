"""
Collect per-test coverage and repeated timings for one Python project.

Example (from the project root, with the target project cloned and its
test dependencies installed in the same environment):

    python collect_project.py --project data/raw/tinydb --name tinydb
    python collect_project.py --project data/raw/tinydb --name tinydb --coverage-only

Writes to data/processed/:
    <name>_coverage_matrix.csv   test_node_id, source_file, covered_lines
    <name>_timing_runs.csv       project, run_number, node_id, status, duration_seconds
    <name>_source.json           commit hash of the project that was measured
and then rebuilds <name>_kalman_estimates.csv.
"""

import argparse
import csv
import json
import subprocess
from pathlib import Path

from src.collect.test_discovery import discover_test_cases
from src.collect.coverage_collector import collect_test_coverage
from src.collect.timing_collector import collect_repeated_timings
from build_kalman_estimates import build_estimates

OUTPUT_DIR = Path("data/processed")


def batches(items, size):
    for start in range(0, len(items), size):
        yield start, items[start:start + size]


def collect_coverage(project_path, name, test_cases, batch_size):
    output_path = OUTPUT_DIR / f"{name}_coverage_matrix.csv"
    rows = []
    with_coverage = set()

    for start, batch in batches(test_cases, batch_size):
        print(f"Coverage: tests {start + 1}-{start + len(batch)} of {len(test_cases)}")
        result = collect_test_coverage(project_path, batch)

        for node_id, files in result["coverage"].items():
            if files:
                with_coverage.add(node_id)

            for source_file, lines in files.items():
                rows.append({
                    "test_node_id": node_id,
                    "source_file": source_file,
                    "covered_lines": ";".join(map(str, lines))
                })

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file, fieldnames=["test_node_id", "source_file", "covered_lines"]
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Tests with coverage: {len(with_coverage)} / {len(test_cases)}")
    print("Saved:", output_path)


def collect_timings(project_path, name, test_cases, batch_size, runs):
    output_path = OUTPUT_DIR / f"{name}_timing_runs.csv"
    fields = ["project", "run_number", "node_id", "status", "duration_seconds"]

    with output_path.open("w", newline="", encoding="utf-8") as final_file:
        writer = csv.DictWriter(final_file, fieldnames=fields)
        writer.writeheader()

        for start, batch in batches(test_cases, batch_size):
            batch_file = OUTPUT_DIR / f"{name}_batch_{start}.csv"
            print(f"Timing: tests {start + 1}-{start + len(batch)}")

            collect_repeated_timings(
                project_path, batch, repetitions=runs, output_path=batch_file
            )

            with batch_file.open(newline="", encoding="utf-8") as source:
                for row in csv.DictReader(source):
                    row["project"] = name
                    writer.writerow(row)

            batch_file.unlink()

    print("Saved:", output_path)


def record_source(project_path, name):
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=project_path,
            capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "unknown"

    path = OUTPUT_DIR / f"{name}_source.json"
    path.write_text(
        json.dumps({"project": name, "commit": commit}, indent=2),
        encoding="utf-8"
    )
    print(f"Commit {commit} recorded in {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="Path to the cloned project")
    parser.add_argument("--name", required=True, help="Short name, e.g. tinydb")
    parser.add_argument("--runs", type=int, default=10, help="Timing runs per test")
    parser.add_argument("--batch-size", type=int, default=40)
    parser.add_argument("--coverage-only", action="store_true")
    parser.add_argument("--timing-only", action="store_true")
    args = parser.parse_args()

    project_path = Path(args.project).resolve()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    test_cases = discover_test_cases(project_path)
    print(f"Discovered {len(test_cases)} tests in {project_path}")

    if not args.timing_only:
        collect_coverage(project_path, args.name, test_cases, args.batch_size)

    if not args.coverage_only:
        collect_timings(project_path, args.name, test_cases, args.batch_size, args.runs)
        build_estimates(args.name)

    record_source(project_path, args.name)


if __name__ == "__main__":
    main()

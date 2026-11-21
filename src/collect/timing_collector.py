
import csv
import json
import subprocess
import sys
from pathlib import Path


def collect_repeated_timings(
    project_path,
    test_cases,
    repetitions=10,
    output_path=None
):
    """Run tests in fresh processes and save repeated timings to CSV."""

    project_path = Path(project_path).resolve()

    if not project_path.is_dir():
        raise NotADirectoryError(project_path)

    if not test_cases:
        raise ValueError("No test cases provided.")

    if repetitions < 1:
        raise ValueError("Repetitions must be at least 1.")

    if output_path is None:
        output_path = (
            project_path / "timing_runs.csv"
        )

    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    node_ids = [test["node_id"] for test in test_cases]

    runner = r'''
import json
import sys
import time
import pytest


node_ids = json.loads(sys.argv[1])


class TimingPlugin:
    __test__ = False

    def __init__(self):
        self.durations = {}
        self.statuses = {}

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_call(self, item):
        start = time.perf_counter()
        yield
        self.durations[item.nodeid] = (
            time.perf_counter() - start
        )

    def pytest_runtest_logreport(self, report):
        if report.failed:
            self.statuses[report.nodeid] = "failed"
        elif report.skipped:
            self.statuses[report.nodeid] = "skipped"
        elif report.when == "call":
            self.statuses[report.nodeid] = "passed"


plugin = TimingPlugin()

exit_code = pytest.main(
    ["-q", "-o", "addopts=", *node_ids],
    plugins=[plugin]
)

results = []

for node_id in node_ids:
    results.append({
        "node_id": node_id,
        "status": plugin.statuses.get(node_id, "not_run"),
        "duration_seconds": plugin.durations.get(
            node_id, 0.0
        )
    })

print("TIMING_RESULTS:" + json.dumps({
    "exit_code": int(exit_code),
    "results": results
}))
'''

    all_results = []

    for run_number in range(1, repetitions + 1):

        print(
            f"Starting timing run {run_number}/{repetitions}..."
        )

        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                runner,
                json.dumps(node_ids)
            ],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        marker = "TIMING_RESULTS:"
        run_data = None

        for line in reversed(completed.stdout.splitlines()):
            if line.startswith(marker):
                run_data = json.loads(line[len(marker):])
                break

        if run_data is None:
            raise RuntimeError(
                f"Timing run {run_number} failed.\n"
                f"Output:\n{completed.stdout}\n"
                f"Errors:\n{completed.stderr}"
            )

        for result in run_data["results"]:
            all_results.append({
                "project": project_path.name,
                "run_number": run_number,
                "node_id": result["node_id"],
                "status": result["status"],
                "duration_seconds": result["duration_seconds"]
            })

        print(
            f"Run {run_number} completed: "
            f"{sum(r['status'] == 'passed' for r in run_data['results'])} passed, "
            f"{sum(r['status'] == 'failed' for r in run_data['results'])} failed"
        )

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as csv_file:

        fieldnames = [
            "project",
            "run_number",
            "node_id",
            "status",
            "duration_seconds"
        ]

        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(all_results)

    print("\nTiming collection completed.")
    print("Total measurements:", len(all_results))
    print("CSV saved to:", output_path)

    return all_results


import os
import time
from pathlib import Path

import pytest


class TestTimingPlugin:
    """Collect individual pytest execution times and outcomes."""

    __test__ = False

    def __init__(self):
        self.durations = {}
        self.statuses = {}

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_call(self, item):
        start = time.perf_counter()
        yield
        self.durations[item.nodeid] = time.perf_counter() - start

    def pytest_runtest_logreport(self, report):
        if report.failed:
            self.statuses[report.nodeid] = "failed"
        elif report.skipped:
            self.statuses[report.nodeid] = "skipped"
        elif report.when == "call":
            self.statuses[report.nodeid] = "passed"


def run_discovered_tests(project_path, test_cases):
    """Run discovered tests and record their individual results."""

    project_path = Path(project_path).resolve()

    if not project_path.is_dir():
        raise NotADirectoryError(
            f"Project directory does not exist: {project_path}"
        )

    if not test_cases:
        raise ValueError("No test cases were provided.")

    node_ids = [test["node_id"] for test in test_cases]

    plugin = TestTimingPlugin()
    original_directory = Path.cwd()

    try:
        os.chdir(project_path)
        exit_code = pytest.main(["-q", *node_ids], plugins=[plugin])
    finally:
        os.chdir(original_directory)

    results = []

    for node_id in node_ids:
        results.append({
            "node_id": node_id,
            "status": plugin.statuses.get(node_id, "not_run"),
            "duration_seconds": plugin.durations.get(node_id, 0.0)
        })

    return {
        "results": results,
        "pytest_exit_code": int(exit_code),
        "total_tests": len(results),
        "passed": sum(r["status"] == "passed" for r in results),
        "failed": sum(r["status"] == "failed" for r in results),
        "skipped": sum(r["status"] == "skipped" for r in results)
    }

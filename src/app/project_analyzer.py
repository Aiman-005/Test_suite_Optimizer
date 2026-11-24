
import csv
from pathlib import Path

from src.collect.test_discovery import discover_test_cases
from src.collect.test_executor import run_discovered_tests
from src.collect.coverage_collector import collect_test_coverage

from src.core.test_suite import TestSuite
from src.core.selection_problem import SelectionProblem


def load_duration_estimates(csv_path):
    """Load Kalman-filtered test durations from a CSV file."""

    estimates = {}

    with Path(csv_path).open(
        "r",
        newline="",
        encoding="utf-8"
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            # Accept both the current and the older column names.
            node_id = row.get("test_node_id") or row.get("node_id")
            duration = float(
                row.get("kalman_estimate_seconds")
                or row.get("estimated_duration")
            )

            if duration > 0:
                estimates[node_id] = duration

    return estimates


def analyze_project(
    project_path,
    budget,
    timing_estimates_path=None
):
    """
    Analyze a Python project and build its test selection problem.

    Uses Kalman estimates when a timing CSV is provided.
    Otherwise, uses measured execution durations.
    """

    project_path = Path(project_path).resolve()

    if not project_path.exists():
        raise FileNotFoundError(
            f"Project directory does not exist: {project_path}"
        )

    if not project_path.is_dir():
        raise NotADirectoryError(
            f"Expected a project directory: {project_path}"
        )

    # Step 1: Discover tests.
    test_cases = discover_test_cases(project_path)

    if not test_cases:
        raise ValueError(
            "No pytest test cases were discovered in the project."
        )

    # Step 2: Execute tests.
    execution_result = run_discovered_tests(
        project_path,
        test_cases
    )

    # Step 3: Collect per-test coverage.
    coverage_result = collect_test_coverage(
        project_path,
        test_cases
    )

    # Step 4: Load optional Kalman estimates.
    duration_estimates = None

    if timing_estimates_path is not None:
        timing_estimates_path = Path(timing_estimates_path)

        if not timing_estimates_path.is_file():
            raise FileNotFoundError(
                f"Timing estimates file not found: "
                f"{timing_estimates_path}"
            )

        duration_estimates = load_duration_estimates(
            timing_estimates_path
        )

    execution_by_id = {
        result["node_id"]: result
        for result in execution_result["results"]
    }

    coverage_by_id = coverage_result["coverage"]

    test_names = []
    durations = {}
    coverage = {}
    excluded_tests = []

    # Step 5: Combine test results, durations, and coverage.
    for test in test_cases:

        node_id = test["node_id"]
        execution = execution_by_id.get(node_id)

        if execution is None or execution["status"] != "passed":
            excluded_tests.append(node_id)
            continue

        if duration_estimates is not None:
            duration = duration_estimates.get(node_id)
        else:
            duration = execution["duration_seconds"]

        if (
            not isinstance(duration, (int, float))
            or duration <= 0
        ):
            excluded_tests.append(node_id)
            continue

        covered_lines = set()

        for source_file, line_numbers in (
            coverage_by_id.get(node_id, {}).items()
        ):
            for line_number in line_numbers:
                covered_lines.add(
                    f"{source_file}:{line_number}"
                )

        test_names.append(node_id)
        durations[node_id] = duration
        coverage[node_id] = covered_lines

    if not test_names:
        raise ValueError(
            "No successfully executed tests with valid durations "
            "are available for optimization."
        )

    # Step 6: Build optimization problem.
    suite = TestSuite(
        test_names,
        durations,
        coverage
    )

    problem = SelectionProblem(
        suite,
        budget=budget
    )

    return {
        "problem": problem,
        "project_path": str(project_path),
        "discovered_tests": len(test_cases),
        "included_tests": len(test_names),
        "excluded_tests": excluded_tests,
        "duration_source": (
            "kalman_estimates"
            if duration_estimates is not None
            else "execution_measurements"
        ),
        "execution_result": execution_result,
        "coverage_result": coverage_result,
        "suite_summary": suite.summary()
    }

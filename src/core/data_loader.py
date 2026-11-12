
import json

from src.core.test_suite import TestSuite
from src.core.selection_problem import SelectionProblem


def load_problem(file_path):
    """
    Load test execution and coverage data from a JSON file.

    Convert the data into a SelectionProblem.
    """

    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    required_fields = {"project_name", "budget", "tests"}

    if not required_fields.issubset(data):
        raise ValueError("Dataset is missing required fields.")

    tests = data["tests"]

    if not isinstance(tests, list) or not tests:
        raise ValueError("Dataset must contain a non-empty test list.")

    test_names = []
    durations = {}
    coverage = {}

    for test in tests:
        if not isinstance(test, dict):
            raise ValueError("Each test must be a JSON object.")

        if not {"name", "duration", "coverage"}.issubset(test):
            raise ValueError("A test is missing required information.")

        name = test["name"]

        if not isinstance(name, str) or not name:
            raise ValueError("Test names must be non-empty strings.")

        if name in durations:
            raise ValueError(f"Duplicate test name: {name}")

        if not isinstance(test["coverage"], list):
            raise ValueError("Test coverage must be a list.")

        test_names.append(name)
        durations[name] = test["duration"]
        coverage[name] = set(test["coverage"])

    suite = TestSuite(
        test_names,
        durations,
        coverage
    )

    return SelectionProblem(
        suite,
        budget=data["budget"]
    )

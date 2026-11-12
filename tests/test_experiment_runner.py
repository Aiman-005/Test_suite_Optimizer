
from pathlib import Path

from src.core.data_loader import load_problem
from src.app.experiment_runner import run_all_optimizers


def load_sample_problem():
    """Load the project's sample dataset."""

    project_root = Path(__file__).resolve().parents[1]

    dataset_path = (
        project_root / "data" / "processed" / "sample_project.json"
    )

    return load_problem(dataset_path)


def test_all_optimizers_run():
    problem = load_sample_problem()

    results = run_all_optimizers(problem)

    expected_algorithms = {
        "Random Selection",
        "Greedy",
        "Hill Climbing",
        "Simulated Annealing",
        "UCS",
        "A*",
        "CSP"
    }

    assert set(results.keys()) == expected_algorithms


def test_all_optimizer_results_are_feasible():
    problem = load_sample_problem()

    results = run_all_optimizers(problem)

    for result in results.values():

        assert result["feasible"] is True

        assert result["total_time"] <= problem.budget


def test_all_optimizers_return_valid_test_names():
    problem = load_sample_problem()

    results = run_all_optimizers(problem)

    for result in results.values():

        for test in result["selected_tests"]:

            assert test in problem.suite.tests

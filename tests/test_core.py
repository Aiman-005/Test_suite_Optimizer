
import pytest

from src.core.test_suite import TestSuite
from src.core.selection_problem import SelectionProblem


@pytest.fixture
def sample_suite():
    """Create a small test suite for automated testing."""

    tests = ["test_login", "test_signup", "test_payment"]

    durations = {
        "test_login": 2,
        "test_signup": 3,
        "test_payment": 4
    }

    coverage = {
        "test_login": {1, 2, 3},
        "test_signup": {2, 3, 4},
        "test_payment": {5, 6}
    }

    return TestSuite(tests, durations, coverage)


def test_total_execution_time(sample_suite):
    assert sample_suite.time_of(sample_suite.tests) == 9


def test_coverage_calculation(sample_suite):
    covered = sample_suite.coverage_of(
        ["test_login", "test_signup"]
    )

    assert covered == {1, 2, 3, 4}


def test_total_coverable_lines(sample_suite):
    assert sample_suite.total_coverable_lines() == 6


def test_feasible_selection(sample_suite):
    problem = SelectionProblem(sample_suite, budget=6)

    assert problem.is_feasible(
        ["test_login", "test_payment"]
    )


def test_infeasible_selection(sample_suite):
    problem = SelectionProblem(sample_suite, budget=5)

    assert not problem.is_feasible(
        ["test_login", "test_payment"]
    )


def test_coverage_percentage(sample_suite):
    problem = SelectionProblem(sample_suite, budget=6)

    result = problem.coverage_score(
        ["test_login", "test_payment"]
    )

    assert result == pytest.approx(83.333333, rel=1e-5)


def test_unknown_test(sample_suite):
    with pytest.raises(ValueError):
        sample_suite.time_of(["test_unknown"])


def test_invalid_duration():
    with pytest.raises(ValueError):
        TestSuite(
            ["test_login"],
            {"test_login": -2},
            {"test_login": {1, 2}}
        )

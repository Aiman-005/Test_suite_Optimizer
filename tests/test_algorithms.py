import pytest
from src.core.test_suite import TestSuite
from src.core.selection_problem import SelectionProblem
from src.algorithms.random_selection import RandomSelectionOptimizer
from src.algorithms.greedy import GreedyOptimizer
from src.algorithms.hill_climbing import HillClimbingOptimizer
from src.algorithms.simulated_annealing import SimulatedAnnealingOptimizer
from src.algorithms.search_optimization import SearchOptimizer
from src.algorithms.csp_optimizer import CSPOptimizer

def create_sample_problem():
    """Create a small test-selection problem."""

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

    suite = TestSuite(tests, durations, coverage)

    return SelectionProblem(suite, budget=6)


def test_random_selection_respects_budget():
    problem = create_sample_problem()

    optimizer = RandomSelectionOptimizer(problem, seed=42)

    selected = optimizer.optimize()

    assert problem.is_feasible(selected)


def test_random_selection_is_reproducible():
    problem = create_sample_problem()

    optimizer1 = RandomSelectionOptimizer(problem, seed=42)
    optimizer2 = RandomSelectionOptimizer(problem, seed=42)

    assert optimizer1.optimize() == optimizer2.optimize()

def test_greedy_selection_respects_budget():
    problem = create_sample_problem()

    optimizer = GreedyOptimizer(problem)

    selected = optimizer.optimize()

    assert problem.is_feasible(selected)


def test_greedy_selection_gets_best_sample_coverage():
    problem = create_sample_problem()

    optimizer = GreedyOptimizer(problem)

    selected = optimizer.optimize()

    result = problem.evaluate(selected)

    assert result["coverage_percentage"] == pytest.approx(83.333333)
    assert result["total_time"] == 6
    assert result["feasible"]

def test_hill_climbing_respects_budget():
    problem = create_sample_problem()

    optimizer = HillClimbingOptimizer(
        problem,
        max_restarts=10,
        seed=42
    )

    selected = optimizer.optimize()

    assert problem.is_feasible(selected)


def test_hill_climbing_finds_best_sample_coverage():
    problem = create_sample_problem()

    optimizer = HillClimbingOptimizer(
        problem,
        max_restarts=10,
        seed=42
    )

    selected = optimizer.optimize()

    result = problem.evaluate(selected)

    assert result["coverage_percentage"] == pytest.approx(83.333333)
    assert result["feasible"]

def test_simulated_annealing_respects_budget():
    problem = create_sample_problem()

    optimizer = SimulatedAnnealingOptimizer(
        problem,
        seed=42
    )

    selected = optimizer.optimize()

    assert problem.is_feasible(selected)


def test_simulated_annealing_finds_best_sample_coverage():
    problem = create_sample_problem()

    optimizer = SimulatedAnnealingOptimizer(
        problem,
        seed=42
    )

    selected = optimizer.optimize()

    result = problem.evaluate(selected)

    assert result["coverage_percentage"] == pytest.approx(83.333333)
    assert result["feasible"]

def test_ucs_respects_budget():
    problem = create_sample_problem()

    optimizer = SearchOptimizer(problem)

    selected = optimizer.uniform_cost_search()

    assert problem.is_feasible(selected)


def test_astar_respects_budget():
    problem = create_sample_problem()

    optimizer = SearchOptimizer(problem)

    selected = optimizer.a_star_search()

    assert problem.is_feasible(selected)


def test_ucs_finds_best_sample_coverage():
    problem = create_sample_problem()

    optimizer = SearchOptimizer(problem)

    selected = optimizer.uniform_cost_search()

    result = problem.evaluate(selected)

    assert result["coverage_percentage"] == pytest.approx(83.333333)


def test_astar_finds_best_sample_coverage():
    problem = create_sample_problem()

    optimizer = SearchOptimizer(problem)

    selected = optimizer.a_star_search()

    result = problem.evaluate(selected)

    assert result["coverage_percentage"] == pytest.approx(83.333333)


def test_csp_respects_budget():
    problem = create_sample_problem()

    optimizer = CSPOptimizer(problem)

    selected = optimizer.optimize()

    assert problem.is_feasible(selected)


def test_csp_finds_best_sample_coverage():
    problem = create_sample_problem()

    optimizer = CSPOptimizer(problem)

    selected = optimizer.optimize()

    result = problem.evaluate(selected)

    assert result["coverage_percentage"] == pytest.approx(83.333333)
    assert result["total_time"] == 6


def test_csp_returns_valid_test_names():
    problem = create_sample_problem()

    optimizer = CSPOptimizer(problem)

    selected = optimizer.optimize()

    assert set(selected).issubset(set(problem.suite.tests))

import itertools
import random
from src.core.test_suite import TestSuite
from src.core.selection_problem import SelectionProblem
from src.algorithms.greedy import GreedyOptimizer
from src.algorithms.hill_climbing import HillClimbingOptimizer
from src.algorithms.simulated_annealing import SimulatedAnnealingOptimizer
from src.algorithms.search_optimization import UniformCostSearch, AStarSearch, SearchSolver
from src.algorithms.base import Optimizer
from src.algorithms.random_selection import RandomSelectionOptimizer
from src.algorithms.csp_optimizer import CSPOptimizer
from src.algorithms.selection_state import SelectionState

def random_problem(seed, n_tests=10, n_lines=30, budget_fraction=0.4):
    """A random but reproducible selection problem."""

    rng = random.Random(seed)
    tests = [f"t{i}" for i in range(n_tests)]
    durations = {t: round(rng.uniform(0.5, 5.0), 2) for t in tests}
    coverage = {
        t: set(rng.sample(range(n_lines), rng.randint(1, 8))) for t in tests
    }
    suite = TestSuite(tests, durations, coverage)
    return SelectionProblem(suite, suite.time_of(tests) * budget_fraction)


def best_coverage_brute_force(problem):
    tests = problem.suite.tests
    best = 0
    for r in range(len(tests) + 1):
        for combo in itertools.combinations(tests, r):
            if problem.is_feasible(combo):
                best = max(best, len(problem.suite.coverage_of(combo)))
    return best


def test_selection_state_matches_full_recomputation():
    problem = random_problem(0)
    state = SelectionState(problem)
    rng = random.Random(1)

    for _ in range(300):
        unselected = [t for t in problem.suite.tests if t not in state.selected_set]
        kind = rng.choice(["add", "remove", "swap"])

        if kind == "add" and unselected or not state.selected:
            move = ("add", rng.choice(unselected), None)
        elif kind == "remove" or not unselected:
            move = ("remove", rng.choice(state.selected), None)
        else:
            move = ("swap", rng.choice(state.selected), rng.choice(unselected))

        covered, time = state.evaluate(*move)
        state.apply(*move)

        assert covered == state.covered == len(problem.suite.coverage_of(state.selected))
        assert abs(time - problem.suite.time_of(state.selected)) < 1e-9


def test_local_search_is_never_worse_than_greedy_and_feasible():
    for seed in range(5):
        problem = random_problem(seed)
        greedy = problem.coverage_score(GreedyOptimizer(problem).optimize())

        for optimizer in (
            HillClimbingOptimizer(problem, seed=seed),
            SimulatedAnnealingOptimizer(problem, seed=seed),
        ):
            selected = optimizer.optimize()
            assert problem.is_feasible(selected)
            assert problem.coverage_score(selected) >= greedy - 1e-9
            assert optimizer.history, "history should be recorded"


def test_full_coverage_ucs_and_astar_find_the_cheapest_cover():
    for seed in range(5):
        suite = random_problem(seed, n_tests=9).suite
        all_lines = set().union(*suite.coverage.values())

        cheapest = min(
            suite.time_of(combo)
            for r in range(1, len(suite.tests) + 1)
            for combo in itertools.combinations(suite.tests, r)
            if suite.coverage_of(combo) == all_lines
        )

        ucs = UniformCostSearch(suite)
        astar = AStarSearch(suite)
        ucs_tests = ucs.search()
        astar_tests = astar.search()

        assert abs(ucs.cost - cheapest) < 1e-9
        assert abs(astar.cost - cheapest) < 1e-9
        assert suite.coverage_of(ucs_tests) == all_lines
        assert suite.coverage_of(astar_tests) == all_lines
        assert astar.nodes_expanded <= ucs.nodes_expanded


def test_astar_heuristic_is_admissible_at_the_start():
    for seed in range(5):
        suite = random_problem(seed, n_tests=9).suite
        ucs = UniformCostSearch(suite)
        ucs.search()
        assert AStarSearch(suite).heuristic(frozenset()) <= ucs.cost + 1e-9


def test_csp_variants_agree_and_mrv_needs_fewer_backtracks():
    for seed in range(5):
        problem = random_problem(seed)
        optimum = best_coverage_brute_force(problem)

        plain = CSPOptimizer(problem, use_mrv=False, forward_checking=False)
        smart = CSPOptimizer(problem, use_mrv=True, forward_checking=True)

        assert len(problem.suite.coverage_of(plain.optimize())) == optimum
        assert len(problem.suite.coverage_of(smart.optimize())) == optimum
        assert smart.backtracks <= plain.backtracks

def test_class_hierarchy_matches_the_design():
    problem = random_problem(0)

    for optimizer in (
        RandomSelectionOptimizer(problem, seed=0),
        GreedyOptimizer(problem),
        HillClimbingOptimizer(problem, seed=0),
        SimulatedAnnealingOptimizer(problem, seed=0),
        CSPOptimizer(problem),
    ):
        assert isinstance(optimizer, Optimizer)
        result = optimizer.solve()
        assert result["feasible"]
        assert result["optimizer"] == optimizer.name

    assert issubclass(UniformCostSearch, SearchSolver)
    assert issubclass(AStarSearch, UniformCostSearch)
    assert AStarSearch.priority is not UniformCostSearch.priority

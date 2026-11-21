
import time

from src.algorithms.random_selection import RandomSelectionOptimizer
from src.algorithms.greedy import GreedyOptimizer
from src.algorithms.hill_climbing import HillClimbingOptimizer
from src.algorithms.simulated_annealing import SimulatedAnnealingOptimizer
from src.algorithms.search_optimization import SearchOptimizer
from src.algorithms.csp_optimizer import CSPOptimizer


def run_all_optimizers(problem, seed=42):
    """
    Run all optimization algorithms and collect their results,
    including optimizer execution time.
    """

    optimizers = {
        "Random Selection": RandomSelectionOptimizer(
            problem, seed=seed
        ),
        "Greedy": GreedyOptimizer(problem),
        "Hill Climbing": HillClimbingOptimizer(
        problem, max_restarts=1, max_neighbors=20,
        max_steps=20, seed=seed
        ),
        "Simulated Annealing": SimulatedAnnealingOptimizer(
            problem, initial_temperature=100,
            cooling_rate=0.95,
            iterations=300, seed=seed
        ),
        "UCS": SearchOptimizer(problem),
        "A*": SearchOptimizer(problem),
        "CSP": CSPOptimizer(problem)
    }

    results = {}

    for name, optimizer in optimizers.items():

        start_time = time.perf_counter()

        if name == "UCS":
            selected_tests = optimizer.uniform_cost_search()

        elif name == "A*":
            selected_tests = optimizer.a_star_search()

        else:
            selected_tests = optimizer.optimize()

        end_time = time.perf_counter()

        optimizer_runtime = end_time - start_time

        evaluation = problem.evaluate(selected_tests)

        evaluation["optimizer_runtime_seconds"] = optimizer_runtime

        results[name] = evaluation

    return results

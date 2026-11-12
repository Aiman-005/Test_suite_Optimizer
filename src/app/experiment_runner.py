
from src.algorithms.random_selection import RandomSelectionOptimizer
from src.algorithms.greedy import GreedyOptimizer
from src.algorithms.hill_climbing import HillClimbingOptimizer
from src.algorithms.simulated_annealing import SimulatedAnnealingOptimizer
from src.algorithms.search_optimization import SearchOptimizer
from src.algorithms.csp_optimizer import CSPOptimizer


def run_all_optimizers(problem, seed=42):
    """
    Run all optimization algorithms on the same problem
    and collect their evaluation results.
    """

    optimizers = {
        "Random Selection": RandomSelectionOptimizer(
            problem, seed=seed
        ),
        "Greedy": GreedyOptimizer(problem),
        "Hill Climbing": HillClimbingOptimizer(
            problem, max_restarts=10, seed=seed
        ),
        "Simulated Annealing": SimulatedAnnealingOptimizer(
            problem, seed=seed
        ),
        "UCS": SearchOptimizer(problem),
        "A*": SearchOptimizer(problem),
        "CSP": CSPOptimizer(problem)
    }

    results = {}

    for name, optimizer in optimizers.items():

        if name == "UCS":
            selected_tests = optimizer.uniform_cost_search()

        elif name == "A*":
            selected_tests = optimizer.a_star_search()

        else:
            selected_tests = optimizer.optimize()

        results[name] = problem.evaluate(selected_tests)

    return results

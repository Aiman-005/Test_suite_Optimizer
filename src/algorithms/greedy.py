from src.algorithms.base import Optimizer
class GreedyOptimizer(Optimizer):
    """ Selects tests based on additional code coverage per unit of execution time.
    """

    name = "Greedy"

    def __init__(self, problem):
        super().__init__(problem)

    def optimize(self):
        """Return a greedy test selection within the budget."""

        selected_tests = []
        remaining_tests = self.problem.suite.tests.copy()

        covered_lines = set()
        remaining_budget = self.problem.budget

        while remaining_tests:

            best_test = None
            best_ratio = 0

            for test in remaining_tests:

                duration = self.problem.suite.durations[test]

                if duration > remaining_budget:
                    continue

                new_lines = (
                    self.problem.suite.coverage[test] - covered_lines
                )

                ratio = len(new_lines) / duration

                if ratio > best_ratio:
                    best_ratio = ratio
                    best_test = test

            if best_test is None:
                break

            selected_tests.append(best_test)

            covered_lines.update(
                self.problem.suite.coverage[best_test]
            )

            remaining_budget -= (
                self.problem.suite.durations[best_test]
            )

            remaining_tests.remove(best_test)

        return selected_tests
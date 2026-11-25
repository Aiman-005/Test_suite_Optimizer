from src.algorithms.base import Optimizer
class CSPOptimizer(Optimizer):
    """Solves the test-selection problem using CSP.Each test can be selected (1) or skipped (0).
    The total time of selected tests must stay within the budget.The goal is to get the highest code coverage.
    Options:
    use_mrv: Selects the test with the fewest available choices first.and 
    forward_checking: Skips tests that no longer fit the budget.
    Tracks the number of assignments and backtracks.
    """

    name = "CSP"

    def __init__(self, problem, use_mrv=True, forward_checking=True):
        super().__init__(problem)
        self.use_mrv = use_mrv
        self.forward_checking = forward_checking

        self.best_solution = []
        self.best_coverage = -1
        self.best_time = float("inf")

        self.nodes = 0
        self.backtracks = 0

    def _select_variable(self, domains, unassigned):
        """MRV: smallest remaining domain first; else the next in order."""

        if not self.use_mrv:
            return unassigned[0]

        return min(
            unassigned,
            key=lambda test: (
                len(domains[test]),
                -self.problem.suite.durations[test]
            )
        )

    def _backtrack(self, domains, selected, remaining, used_time):
        """Explore assignments with backtracking."""

        if not remaining:
            coverage = len(self.problem.suite.coverage_of(selected))

            if (
                coverage > self.best_coverage
                or (
                    coverage == self.best_coverage
                    and used_time < self.best_time
                )
            ):
                self.best_solution = selected.copy()
                self.best_coverage = coverage
                self.best_time = used_time

            return

        variable = self._select_variable(domains, remaining)

        next_remaining = [
            test for test in remaining if test != variable
        ]

        # Try selecting the test first, then excluding it.
        for value in domains[variable]:
            self.nodes += 1

            new_selected = selected.copy()
            new_time = used_time

            if value == 1:
                new_selected.append(variable)
                new_time += self.problem.suite.durations[variable]

            # Constraint check: the budget must not be exceeded.
            if new_time > self.problem.budget:
                self.backtracks += 1
                continue

            new_domains = domains

            if self.forward_checking:
                remaining_budget = self.problem.budget - new_time
                new_domains = dict(domains)

                for test in next_remaining:
                    if self.problem.suite.durations[test] > remaining_budget:
                        new_domains[test] = [0]

            self._backtrack(
                new_domains,
                new_selected,
                next_remaining,
                new_time
            )

    def optimize(self):
        """Find the best feasible test selection."""

        self.best_solution = []
        self.best_coverage = -1
        self.best_time = float("inf")
        self.nodes = 0
        self.backtracks = 0

        domains = {
            test: [1, 0]
            for test in self.problem.suite.tests
        }

        self._backtrack(
            domains,
            [],
            self.problem.suite.tests.copy(),
            0.0
        )

        return self.best_solution

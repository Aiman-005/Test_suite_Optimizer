
class CSPOptimizer:
    """
    Solves the test-selection problem using:
    1. Backtracking
    2. Minimum Remaining Values (MRV)
    3. Forward Checking
    """

    def __init__(self, problem):
        self.problem = problem
        self.best_solution = []
        self.best_coverage = -1
        self.best_time = float("inf")

    def _select_mrv_variable(self, domains, unassigned):
        """Choose the variable with the smallest remaining domain."""

        return min(
            unassigned,
            key=lambda test: (
                len(domains[test]),
                -self.problem.suite.durations[test]
            )
        )

    def _backtrack(self, domains, selected, remaining):
        """Explore assignments using backtracking and forward checking."""

        if not remaining:
            coverage = len(
                self.problem.suite.coverage_of(selected)
            )

            execution_time = self.problem.suite.time_of(selected)

            if (
                coverage > self.best_coverage
                or (
                    coverage == self.best_coverage
                    and execution_time < self.best_time
                )
            ):
                self.best_solution = selected.copy()
                self.best_coverage = coverage
                self.best_time = execution_time

            return

        variable = self._select_mrv_variable(domains, remaining)

        next_remaining = [
            test for test in remaining if test != variable
        ]

        # Try selecting the test first, then excluding it.
        for value in domains[variable]:

            new_selected = selected.copy()

            if value == 1:
                new_selected.append(variable)

            current_time = self.problem.suite.time_of(new_selected)

            if current_time > self.problem.budget:
                continue

            remaining_budget = self.problem.budget - current_time

            # Forward checking: update remaining domains.
            new_domains = {
                test: choices.copy()
                for test, choices in domains.items()
            }

            for test in next_remaining:
                duration = self.problem.suite.durations[test]

                if duration > remaining_budget:
                    new_domains[test] = [0]

            self._backtrack(
                new_domains,
                new_selected,
                next_remaining
            )

    def optimize(self):
        """Find the best feasible test selection."""

        self.best_solution = []
        self.best_coverage = -1
        self.best_time = float("inf")

        domains = {
            test: [1, 0]
            for test in self.problem.suite.tests
        }

        self._backtrack(
            domains,
            [],
            self.problem.suite.tests.copy()
        )

        return self.best_solution

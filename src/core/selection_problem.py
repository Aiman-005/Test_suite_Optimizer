
class SelectionProblem:
    """
    Defines the test-selection optimization problem.

    The objective is to maximize code coverage
    without exceeding the execution-time budget.
    """

    def __init__(self, suite, budget):
        self.suite = suite
        self.budget = budget

        if not isinstance(budget, (int, float)) or budget <= 0:
            raise ValueError("Budget must be a positive number.")

    def is_feasible(self, selected_tests):
        """Check whether selected tests fit within the budget."""

        total_time = self.suite.time_of(selected_tests)

        return total_time <= self.budget

    def coverage_score(self, selected_tests):
        """Calculate the percentage of coverable lines covered."""

        total_lines = self.suite.total_coverable_lines()

        if total_lines == 0:
            return 0.0

        covered_lines = self.suite.coverage_of(selected_tests)

        return (len(covered_lines) / total_lines) * 100

    def fitness(self, selected_tests):
        """
        Calculate solution fitness.

        Feasible selections are scored by coverage.
        Infeasible selections receive a penalty.
        """

        total_time = self.suite.time_of(selected_tests)
        coverage = self.coverage_score(selected_tests)

        if total_time <= self.budget:
            return coverage

        over_budget = total_time - self.budget

        return coverage - (over_budget / self.budget * 100)

    def evaluate(self, selected_tests):
        """Return all important measurements for a selection."""

        return {
            "selected_tests": selected_tests,
            "total_time": self.suite.time_of(selected_tests),
            "budget": self.budget,
            "feasible": self.is_feasible(selected_tests),
            "coverage_percentage": self.coverage_score(selected_tests),
            "fitness": self.fitness(selected_tests)
        }

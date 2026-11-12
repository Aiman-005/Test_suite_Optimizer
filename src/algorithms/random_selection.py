import random


class RandomSelectionOptimizer:
    """
    Selects test cases randomly while respecting
    the available execution-time budget.
    """

    def __init__(self, problem, seed=None):
        self.problem = problem
        self.random_generator = random.Random(seed)

    def optimize(self):
        """Return a random selection of tests within the budget."""

        tests = self.problem.suite.tests.copy()

        # Shuffle tests to create a random selection order.
        self.random_generator.shuffle(tests)

        selected_tests = []

        # Add a test only if it does not exceed the budget.
        for test in tests:
            candidate = selected_tests + [test]

            if self.problem.is_feasible(candidate):
                selected_tests.append(test)

        return selected_tests
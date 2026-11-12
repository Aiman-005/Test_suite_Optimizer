import random


class HillClimbingOptimizer:
    """
    Improves a test selection by exploring nearby solutions.

    Uses random restarts to reduce the chance of getting
    stuck at a local optimum.
    """

    def __init__(self, problem, max_restarts=10, seed=None):
        self.problem = problem
        self.max_restarts = max_restarts
        self.random_generator = random.Random(seed)

    def _score(self, selected_tests):
        """Compare solutions by coverage, then execution time."""

        coverage = self.problem.coverage_score(selected_tests)
        execution_time = self.problem.suite.time_of(selected_tests)

        return coverage, -execution_time

    def _create_random_solution(self):
        """Create a random feasible starting selection."""

        tests = self.problem.suite.tests.copy()
        self.random_generator.shuffle(tests)

        selected = []

        for test in tests:
            if self.random_generator.choice([True, False]):
                candidate = selected + [test]

                if self.problem.is_feasible(candidate):
                    selected.append(test)

        return selected

    def _get_neighbors(self, selected):
        """Generate solutions by adding, removing, or swapping tests."""

        all_tests = self.problem.suite.tests
        neighbors = []

        # Try removing one selected test.
        for test in selected:
            candidate = [item for item in selected if item != test]
            neighbors.append(candidate)

        # Try adding one unselected test.
        for test in all_tests:
            if test not in selected:
                candidate = selected + [test]

                if self.problem.is_feasible(candidate):
                    neighbors.append(candidate)

        # Try replacing one selected test with another.
        for old_test in selected:
            for new_test in all_tests:
                if new_test not in selected:
                    candidate = [
                        item for item in selected if item != old_test
                    ]
                    candidate.append(new_test)

                    if self.problem.is_feasible(candidate):
                        neighbors.append(candidate)

        return neighbors

    def _climb(self, current):
        """Keep moving to a better neighboring solution."""

        while True:
            best_neighbor = current
            best_score = self._score(current)

            for neighbor in self._get_neighbors(current):
                score = self._score(neighbor)

                if score > best_score:
                    best_neighbor = neighbor
                    best_score = score

            if best_neighbor == current:
                break

            current = best_neighbor

        return current

    def optimize(self):
        """Run Hill Climbing with multiple random restarts."""

        best_solution = []
        best_score = self._score(best_solution)

        for _ in range(self.max_restarts):
            starting_solution = self._create_random_solution()
            solution = self._climb(starting_solution)

            score = self._score(solution)

            if score > best_score:
                best_solution = solution
                best_score = score

        return best_solution
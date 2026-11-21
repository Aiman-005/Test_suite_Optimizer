
import random


class HillClimbingOptimizer:
    """
    Randomized-neighborhood Hill Climbing.
    Samples a limited number of neighbors to handle larger test suites.
    """

    def __init__(
        self, problem, max_restarts=1, max_neighbors=20,
        max_steps=20, seed=None
    ):
        self.problem = problem
        self.max_restarts = max_restarts
        self.max_neighbors = max_neighbors
        self.max_steps = max_steps
        self.random_generator = random.Random(seed)

    def _score(self, selected_tests):
        coverage = self.problem.coverage_score(selected_tests)
        execution_time = self.problem.suite.time_of(selected_tests)
        return coverage, -execution_time

    def _create_random_solution(self):
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
        all_tests = self.problem.suite.tests
        selected_set = set(selected)
        unselected = [t for t in all_tests if t not in selected_set]

        operations = (
            [("remove", test, None) for test in selected]
            + [("add", test, None) for test in unselected]
            + [
                ("swap", old, new)
                for old in selected
                for new in unselected
            ]
        )

        if len(operations) > self.max_neighbors:
            operations = self.random_generator.sample(
                operations, self.max_neighbors
            )

        neighbors = []

        for operation, first, second in operations:
            if operation == "remove":
                candidate = [t for t in selected if t != first]

            elif operation == "add":
                candidate = selected + [first]

            else:
                candidate = [t for t in selected if t != first]
                candidate.append(second)

            if self.problem.is_feasible(candidate):
                neighbors.append(candidate)

        return neighbors

    def _climb(self, current):
        for _ in range(self.max_steps):
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

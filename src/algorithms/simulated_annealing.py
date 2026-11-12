import math
import random


class SimulatedAnnealingOptimizer:
    """
    Optimizes test selection using simulated annealing.

    Occasionally accepts worse solutions to escape
    local optima, especially at higher temperatures.
    """

    def __init__(
        self,
        problem,
        initial_temperature=100,
        cooling_rate=0.95,
        iterations=1000,
        seed=None
    ):
        self.problem = problem
        self.initial_temperature = initial_temperature
        self.cooling_rate = cooling_rate
        self.iterations = iterations
        self.random_generator = random.Random(seed)

    def _score(self, selected):
        coverage = self.problem.coverage_score(selected)
        execution_time = self.problem.suite.time_of(selected)

        return coverage, -execution_time

    def _create_neighbor(self, current):
        """Create a nearby feasible solution."""

        tests = self.problem.suite.tests
        candidate = current.copy()

        if not tests:
            return candidate

        test = self.random_generator.choice(tests)

        if test in candidate:
            candidate.remove(test)
        else:
            candidate.append(test)

        if self.problem.is_feasible(candidate):
            return candidate

        return current.copy()

    def optimize(self):
        """Run the simulated annealing optimization process."""

        current = []
        best_solution = current.copy()

        temperature = self.initial_temperature

        for _ in range(self.iterations):

            candidate = self._create_neighbor(current)

            current_score = self._score(current)
            candidate_score = self._score(candidate)

            difference = (
                candidate_score[0] - current_score[0]
            )

            if difference > 0:
                current = candidate

            elif difference == 0:
                if candidate_score[1] > current_score[1]:
                    current = candidate

            else:
                probability = math.exp(
                    difference / max(temperature, 1e-10)
                )

                if self.random_generator.random() < probability:
                    current = candidate

            if self._score(current) > self._score(best_solution):
                best_solution = current.copy()

            temperature *= self.cooling_rate

        return best_solution
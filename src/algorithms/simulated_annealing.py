import math
import random

from src.algorithms.greedy import GreedyOptimizer
from src.algorithms.selection_state import SelectionState
from src.algorithms.base import Optimizer


class SimulatedAnnealingOptimizer(Optimizer):
    """
    Optimizes test selection using simulated annealing (Lab 06).

    Starts from the greedy solution, proposes add / remove / swap moves,
    and accepts a worse move with probability exp(delta / T), where
    delta is the change in the number of covered lines (so T is in
    "lines"). The temperature cools geometrically:
    T <- T * cooling_rate after every iteration.
    """

    name = "Simulated Annealing"

    def __init__(
        self,
        problem,
        initial_temperature=2.0,
        cooling_rate=0.9995,
        iterations=20000,
        seed=None,
        greedy_start=True
    ):
        super().__init__(problem)
        self.initial_temperature = initial_temperature
        self.cooling_rate = cooling_rate
        self.iterations = iterations
        self.greedy_start = greedy_start
        self.random_generator = random.Random(seed)

        # Best coverage (%) after every iteration (for convergence charts).
        self.history = []

    def _sample_move(self, state):
        tests = self.problem.suite.tests
        move = self.random_generator.choice(["add", "remove", "swap"])

        if move == "remove" and state.selected:
            return "remove", self.random_generator.choice(state.selected), None

        # Draw an unselected test by rejection sampling (fast for big suites).
        new = None
        if len(state.selected_set) < len(tests):
            while new is None or new in state.selected_set:
                new = self.random_generator.choice(tests)

        if new is None:
            return None

        if move == "add" or not state.selected:
            return "add", new, None

        return "swap", self.random_generator.choice(state.selected), new

    def optimize(self):
        """Run the simulated annealing optimization process."""

        self.history = []

        start = (
            GreedyOptimizer(self.problem).optimize()
            if self.greedy_start else []
        )
        state = SelectionState(self.problem, start)

        best_solution = state.selected.copy()
        best_score = state.score()

        temperature = self.initial_temperature

        for _ in range(self.iterations):

            move = self._sample_move(state)

            if move is not None:
                covered, time = state.evaluate(*move)

                if time <= self.problem.budget:
                    difference = covered - state.covered

                    if difference > 0 or (
                        difference == 0 and time <= state.time
                    ):
                        accept = True
                    else:
                        probability = math.exp(
                            difference / max(temperature, 1e-10)
                        )
                        accept = self.random_generator.random() < probability

                    if accept:
                        state.apply(*move)

                        if state.score() > best_score:
                            best_solution = state.selected.copy()
                            best_score = state.score()

            self.history.append(best_score[0])
            temperature *= self.cooling_rate

        return best_solution

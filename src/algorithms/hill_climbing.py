
import random

from src.algorithms.greedy import GreedyOptimizer
from src.algorithms.selection_state import SelectionState
from src.algorithms.base import Optimizer


class HillClimbingOptimizer(Optimizer):
    """
    Hill climbing with random restarts (Lab 06).

    The first climb starts from the greedy solution; every other
    restart starts from a random feasible selection. Each step samples
    add / remove / swap neighbours and moves to the best one that
    improves the score (coverage first, then lower execution time).
    The climb stops when no sampled neighbour improves (local optimum)
    or after max_steps.
    """

    name = "Hill Climbing"

    def __init__(
        self, problem, max_restarts=5, max_neighbors=200,
        max_steps=300, seed=None, greedy_start=True
    ):
        super().__init__(problem)
        self.max_restarts = max_restarts
        self.max_neighbors = max_neighbors
        self.max_steps = max_steps
        self.greedy_start = greedy_start
        self.random_generator = random.Random(seed)

        # Best coverage (%) after every step, across all restarts.
        self.history = []

    def _create_random_solution(self):
        tests = self.problem.suite.tests.copy()
        self.random_generator.shuffle(tests)

        selected = []
        used_time = 0.0

        for test in tests:
            duration = self.problem.suite.durations[test]

            if (
                self.random_generator.choice([True, False])
                and used_time + duration <= self.problem.budget
            ):
                selected.append(test)
                used_time += duration

        return selected

    def _sample_move(self, state, unselected):
        move = self.random_generator.choice(["add", "remove", "swap"])

        if move == "add" and unselected:
            return "add", self.random_generator.choice(unselected), None

        if move == "remove" and state.selected:
            return "remove", self.random_generator.choice(state.selected), None

        if state.selected and unselected:
            return (
                "swap",
                self.random_generator.choice(state.selected),
                self.random_generator.choice(unselected)
            )

        return None

    def _climb(self, start, best_overall):
        state = SelectionState(self.problem, start)
        tests = self.problem.suite.tests

        for _ in range(self.max_steps):
            unselected = [t for t in tests if t not in state.selected_set]

            best_move = None
            best_score = state.score()

            for _ in range(self.max_neighbors):
                move = self._sample_move(state, unselected)

                if move is None:
                    continue

                covered, time = state.evaluate(*move)

                if time > self.problem.budget:
                    continue

                score = state.score(covered, time)

                if score > best_score:
                    best_move = move
                    best_score = score

            if best_move is None:
                self.history.append(best_overall)
                break

            state.apply(*best_move)
            best_overall = max(best_overall, state.score()[0])
            self.history.append(best_overall)

        return state, best_overall

    def optimize(self):
        self.history = []

        best_solution = []
        best_score = SelectionState(self.problem).score()
        best_overall = best_score[0]

        for restart in range(self.max_restarts):

            if restart == 0 and self.greedy_start:
                start = GreedyOptimizer(self.problem).optimize()
            else:
                start = self._create_random_solution()

            state, best_overall = self._climb(start, best_overall)

            if state.score() > best_score:
                best_solution = state.selected.copy()
                best_score = state.score()

        return best_solution

"""
Base class shared by every test-selection optimiser (proposal 4.1).

Each optimiser inherits from Optimizer and overrides optimize().
solve() is inherited unchanged: it times optimize() and evaluates the
selection, so every method is measured the same way.
"""

import time
from abc import ABC, abstractmethod


class Optimizer(ABC):
    """Abstract optimiser for a SelectionProblem."""

    name = "Optimizer"

    def __init__(self, problem):
        self.problem = problem

    @abstractmethod
    def optimize(self):
        """Return the list of selected test names."""

    def solve(self):
        """Run optimize() and return the selection with its evaluation."""

        start = time.perf_counter()
        selected = self.optimize()
        runtime = time.perf_counter() - start

        result = self.problem.evaluate(selected)
        result["optimizer"] = self.name
        result["optimizer_runtime_seconds"] = runtime
        return result

    def __repr__(self):
        return f"{self.__class__.__name__}(tests={len(self.problem.suite.tests)}, budget={self.problem.budget:.4f})"

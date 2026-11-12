import heapq
from itertools import count


class SearchOptimizer:
    """
    Implements Uniform Cost Search and A*
    for the test-selection problem.
    """

    def __init__(self, problem):
        self.problem = problem

    def _search(self, use_heuristic=False):
        tests = self.problem.suite.tests

        counter = count()

        # State: (selected tests, next test index)
        start_state = ((), 0)

        frontier = [
            (0, next(counter), start_state)
        ]

        visited = set()
        best_solution = []
        best_coverage = 0

        while frontier:
            priority, _, state = heapq.heappop(frontier)

            selected, index = state
            selected = list(selected)

            if state in visited:
                continue

            visited.add(state)

            coverage = self.problem.coverage_score(selected)

            if (
                coverage > best_coverage
                or (
                    coverage == best_coverage
                    and self.problem.suite.time_of(selected)
                    < self.problem.suite.time_of(best_solution)
                )
            ):
                best_solution = selected
                best_coverage = coverage

            if index >= len(tests):
                continue

            test = tests[index]

            # Option 1: Exclude the current test.
            excluded_state = (
                tuple(selected),
                index + 1
            )

            heapq.heappush(
                frontier,
                (
                    self.problem.suite.time_of(selected),
                    next(counter),
                    excluded_state
                )
            )

            # Option 2: Include the current test if feasible.
            candidate = selected + [test]

            if self.problem.is_feasible(candidate):

                new_cost = self.problem.suite.time_of(candidate)

                heuristic = 0

                if use_heuristic:
                    remaining = tests[index + 1:]

                    possible_lines = set(
                        self.problem.suite.coverage_of(candidate)
                    )

                    for remaining_test in remaining:
                        possible_lines.update(
                            self.problem.suite.coverage[remaining_test]
                        )

                    uncovered = (
                        self.problem.suite.total_coverable_lines()
                        - len(possible_lines)
                    )

                    heuristic = uncovered

                included_state = (
                    tuple(candidate),
                    index + 1
                )

                heapq.heappush(
                    frontier,
                    (
                        new_cost + heuristic,
                        next(counter),
                        included_state
                    )
                )

        return best_solution

    def uniform_cost_search(self):
        """Run Uniform Cost Search."""

        return self._search(use_heuristic=False)

    def a_star_search(self):
        """Run A* Search."""

        return self._search(use_heuristic=True)
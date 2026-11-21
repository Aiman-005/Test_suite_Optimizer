
import heapq
from itertools import count


class SearchOptimizer:
    """
    Implements Uniform Cost Search and A* for test selection.

    The objective is to maximize code coverage without
    exceeding the execution-time budget.

    Small problems can be searched exhaustively.
    Large problems use a configurable state limit.
    """

    def __init__(self, problem, max_states=20000):
        self.problem = problem

        if not isinstance(max_states, int) or max_states <= 0:
            raise ValueError("max_states must be a positive integer.")

        self.max_states = max_states

    def _greedy_initial_solution(self):
        """Generate a feasible starting solution."""

        selected = []
        covered = set()

        remaining = list(self.problem.suite.tests)

        while remaining:
            best_test = None
            best_ratio = 0

            for test in remaining:
                new_lines = (
                    self.problem.suite.coverage[test] - covered
                )

                duration = self.problem.suite.durations[test]

                ratio = len(new_lines) / duration

                if ratio > best_ratio:
                    best_ratio = ratio
                    best_test = test

            if best_test is None:
                break

            candidate = selected + [best_test]

            if self.problem.is_feasible(candidate):
                selected = candidate
                covered.update(
                    self.problem.suite.coverage[best_test]
                )

            remaining.remove(best_test)

        return selected

    def _search(self, use_heuristic=False):
        """Perform bounded best-first test selection."""

        tests = self.problem.suite.tests
        suite = self.problem.suite

        counter = count()

        best_solution = self._greedy_initial_solution()
        best_coverage = len(suite.coverage_of(best_solution))
        best_time = suite.time_of(best_solution)

        # State: (selected tests, next test index, covered lines)
        start_state = ((), 0, frozenset())

        frontier = [
            (0, 0, next(counter), start_state)
        ]

        # Store the cheapest known cost for each equivalent state.
        visited = {}

        expanded_states = 0

        while frontier and expanded_states < self.max_states:

            priority, cost, _, state = heapq.heappop(frontier)

            selected, index, covered = state

            state_key = (index, covered)

            if visited.get(state_key, float("inf")) <= cost:
                continue

            visited[state_key] = cost
            expanded_states += 1

            current_coverage = len(covered)

            # Update the best solution.
            if (
                current_coverage > best_coverage
                or (
                    current_coverage == best_coverage
                    and cost < best_time
                )
            ):
                best_solution = list(selected)
                best_coverage = current_coverage
                best_time = cost

            # No more tests remain.
            if index >= len(tests):
                continue

            # Positive test durations mean no further test can fit.
            if cost >= self.problem.budget:
                continue

            # Calculate the maximum possible coverage from this state.
            possible_coverage = set(covered)

            for remaining_test in tests[index:]:
                possible_coverage.update(
                    suite.coverage[remaining_test]
                )

            maximum_coverage = len(possible_coverage)

            # Branch-and-bound pruning.
            if maximum_coverage < best_coverage:
                continue

            if (
                maximum_coverage == best_coverage
                and cost >= best_time
            ):
                continue

            test = tests[index]

            # Option 1: Exclude the current test.
            excluded_state = (
                selected,
                index + 1,
                covered
            )

            excluded_heuristic = (
                len(possible_coverage) - current_coverage
                if use_heuristic else 0
            )

            heapq.heappush(
                frontier,
                (
                    cost + excluded_heuristic,
                    cost,
                    next(counter),
                    excluded_state
                )
            )

            # Option 2: Include the current test.
            new_cost = cost + suite.durations[test]

            if new_cost <= self.problem.budget:

                new_covered = frozenset(
                    covered | suite.coverage[test]
                )

                included_state = (
                    selected + (test,),
                    index + 1,
                    new_covered
                )

                heuristic = 0

                if use_heuristic:
                    heuristic = (
                        len(possible_coverage) - len(new_covered)
                    )

                heapq.heappush(
                    frontier,
                    (
                        new_cost + heuristic,
                        new_cost,
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

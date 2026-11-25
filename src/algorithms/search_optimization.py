import heapq
from abc import ABC, abstractmethod
from itertools import count
class SearchOptimizer:
    """Implements Uniform Cost Searchand A*.Eac node decides, for the next test in order, whether to include
    or exclude it.A branch-and-bound check prunes nodes that cannot beat the best selection found.
    The objective is to maximize code coverage without exceeding the execution-time budget.
    Small problems can be searched exhaustively.Large problems use a configurable state limit.
    h(n) is the admissible time estimate in heuristic.
    g(n) isthe path cost of the tests includeddd  """

    def __init__(self, problem, max_states=20000):
        self.problem = problem

        if not isinstance(max_states, int) or max_states <= 0:
            raise ValueError("max_states must be a positive integer.")

        self.max_states = max_states

        # Search statistics of the last run (for UCS vs A* comparisons).
        self.nodes_expanded = 0
        self.nodes_generated = 0

    def _heuristic(self, covered, next_index):
        """
        Admissible estimate, in seconds, of the time still needed to
        cover every line that remains reachable from this state.

        h = (reachable lines not yet covered) x (lowest seconds per new
        line offered by any remaining test). Every remaining test costs
        at least that much per new line it covers, so h never
        overestimates the true remaining cost.
        """

        suite = self.problem.suite
        remaining = self.problem.suite.tests[next_index:]

        reachable = set()
        best_rate = float("inf")

        for test in remaining:
            new_lines = suite.coverage[test] - covered

            if new_lines:
                reachable.update(new_lines)
                best_rate = min(
                    best_rate,
                    suite.durations[test] / len(new_lines)
                )

        if not reachable:
            return 0.0

        return len(reachable) * best_rate

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
        generated_states = 1

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
                self._heuristic(covered, index + 1)
                if use_heuristic else 0
            )

            generated_states += 1
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

                heuristic = (
                    self._heuristic(new_covered, index + 1)
                    if use_heuristic else 0
                )

                generated_states += 1
                heapq.heappush(
                    frontier,
                    (
                        new_cost + heuristic,
                        new_cost,
                        next(counter),
                        included_state
                    )
                )

        self.nodes_expanded = expanded_states
        self.nodes_generated = generated_states

        return best_solution

    def uniform_cost_search(self):
        """Run Uniform Cost Search."""

        return self._search(use_heuristic=False)

    def a_star_search(self):
        """Run A* Search."""

        return self._search(use_heuristic=True)



class SearchSolver(ABC):
    """
    Best-first search for the cheapest selection that covers every
    coverable line (proposal 3.3 and 4.1).

    State: the set of lines covered so far (plus the tests chosen).
    Action: add one test that covers the lowest-numbered line not yet
    covered. Path cost g(n): total seconds of the chosen tests.
    Goal test: every coverable line is covered.

    The frontier is a priority queue ordered by priority(), which each
    subclass overrides; explored holds the states already expanded.
    """

    def __init__(self, suite, max_expansions=200000):
        self.suite = suite
        self.max_expansions = max_expansions
        self.all_lines = frozenset(
            line for lines in suite.coverage.values() for line in lines
        )
        self.line_order = sorted(self.all_lines)

        self.frontier = []
        self.explored = set()
        self.nodes_expanded = 0
        self.nodes_generated = 0
        self.cost = None

    @abstractmethod
    def priority(self, cost, covered):
        """Frontier ordering value for a node with path cost g(n) = cost."""

    def search(self):
        """Return the cheapest full-coverage selection (list of tests)."""

        counter = count()
        start = frozenset()
        self.frontier = [(self.priority(0.0, start), 0.0, next(counter), start, ())]
        self.explored = set()
        best_cost = {start: 0.0}
        self.nodes_expanded = 0
        self.nodes_generated = 1
        self.cost = None

        while self.frontier and self.nodes_expanded < self.max_expansions:
            _, cost, _, covered, chosen = heapq.heappop(self.frontier)

            # Skip stale entries; a state is reopened only if reached more
            # cheaply (keeps A* optimal with an admissible heuristic).
            if cost > best_cost.get(covered, float("inf")):
                continue

            self.explored.add(covered)
            self.nodes_expanded += 1

            if covered == self.all_lines:
                self.cost = cost
                return list(chosen)

            target = next(line for line in self.line_order if line not in covered)

            for test in self.suite.tests:
                if target not in self.suite.coverage[test]:
                    continue

                new_covered = covered | self.suite.coverage[test]
                new_cost = cost + self.suite.durations[test]

                if new_cost < best_cost.get(new_covered, float("inf")):
                    best_cost[new_covered] = new_cost
                    self.nodes_generated += 1
                    heapq.heappush(self.frontier, (
                        self.priority(new_cost, new_covered), new_cost,
                        next(counter), new_covered, chosen + (test,)
                    ))

        return None


class UniformCostSearch(SearchSolver):
    """Uniform-cost search (Lab 04): priority = g(n)."""

    def priority(self, cost, covered):
        return cost


class AStarSearch(UniformCostSearch):
    """
    A* search (Lab 05): overrides priority() to g(n) + h(n).

    h is the larger of two lower bounds on the remaining cost:
      1. rate bound: uncovered lines x lowest seconds-per-new-line of
         any test (every uncovered line costs at least that much);
      2. essential-test bound: total seconds of the tests that are the
         only remaining way to cover some uncovered line (they must be
         added in every solution).
    Each bound never overestimates, so their maximum is admissible.
    """

    def heuristic(self, covered):
        uncovered = self.all_lines - covered
        if not uncovered:
            return 0.0

        useful = {
            test: self.suite.coverage[test] & uncovered
            for test in self.suite.tests
            if self.suite.coverage[test] & uncovered
        }

        rate_bound = len(uncovered) * min(
            self.suite.durations[test] / len(lines)
            for test, lines in useful.items()
        )

        coverers = {}
        for test, lines in useful.items():
            for line in lines:
                coverers.setdefault(line, []).append(test)

        essential = {tests[0] for tests in coverers.values() if len(tests) == 1}
        essential_bound = sum(self.suite.durations[test] for test in essential)

        return max(rate_bound, essential_bound)

    def priority(self, cost, covered):
        return cost + self.heuristic(covered)

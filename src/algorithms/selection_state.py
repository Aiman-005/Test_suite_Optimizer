
class SelectionState:
    """
    A test selection with incremental coverage bookkeeping.

    Keeps a count of how many selected tests cover each line, so the
    effect of adding, removing or swapping one test is computed from
    that test's lines only, instead of rebuilding the whole union.
    Used by hill climbing and simulated annealing.
    """

    def __init__(self, problem, selected=()):
        self.problem = problem
        self.suite = problem.suite
        self.total_lines = self.suite.total_coverable_lines()

        self.selected = []
        self.selected_set = set()
        self.line_counts = {}
        self.covered = 0
        self.time = 0.0

        for test in selected:
            self.add(test)

    # ----- evaluation of a move without applying it -----

    def _gain(self, test, removed=None):
        removed_lines = (
            self.suite.coverage[removed] if removed is not None else ()
        )
        gain = 0

        for line in self.suite.coverage[test]:
            count = self.line_counts.get(line, 0)

            if count == 0 or (count == 1 and line in removed_lines):
                gain += 1

        return gain

    def _loss(self, test):
        return sum(
            1 for line in self.suite.coverage[test]
            if self.line_counts.get(line, 0) == 1
        )

    def evaluate(self, move, first, second=None):
        """Return (covered_lines, total_time) after the move."""

        durations = self.suite.durations

        if move == "add":
            return (
                self.covered + self._gain(first),
                self.time + durations[first]
            )

        if move == "remove":
            return (
                self.covered - self._loss(first),
                self.time - durations[first]
            )

        # swap: remove `first`, add `second`
        return (
            self.covered - self._loss(first) + self._gain(second, first),
            self.time - durations[first] + durations[second]
        )

    # ----- applying moves -----

    def add(self, test):
        self.covered += self._gain(test)

        for line in self.suite.coverage[test]:
            self.line_counts[line] = self.line_counts.get(line, 0) + 1

        self.selected.append(test)
        self.selected_set.add(test)
        self.time += self.suite.durations[test]

    def remove(self, test):
        self.covered -= self._loss(test)

        for line in self.suite.coverage[test]:
            self.line_counts[line] -= 1

        self.selected.remove(test)
        self.selected_set.discard(test)
        self.time -= self.suite.durations[test]

    def apply(self, move, first, second=None):
        if move == "add":
            self.add(first)
        elif move == "remove":
            self.remove(first)
        else:
            self.remove(first)
            self.add(second)

    def score(self, covered=None, time=None):
        """Coverage percentage first, then lower time (higher is better)."""

        covered = self.covered if covered is None else covered
        time = self.time if time is None else time
        coverage = (
            covered / self.total_lines * 100 if self.total_lines else 0.0
        )
        return coverage, -time

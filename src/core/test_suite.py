
class TestSuite:
    __test__ = False
    """
    Represents a collection of software test cases.

    Each test has:
    - A unique name
    - An execution time
    - A set of code lines it covers
    """

    def __init__(self, tests, durations, coverage):
        self.tests = tests
        self.durations = durations
        self.coverage = coverage

        self._validate_data()

    def _validate_data(self):
        """Check whether the supplied test data is valid."""

        if not self.tests:
            raise ValueError("Test suite cannot be empty.")

        if len(self.tests) != len(set(self.tests)):
            raise ValueError("Test names must be unique.")

        if set(self.tests) != set(self.durations):
            raise ValueError("Every test must have an execution time.")

        if set(self.tests) != set(self.coverage):
            raise ValueError("Every test must have coverage information.")

        for test, duration in self.durations.items():
            if not isinstance(duration, (int, float)) or duration <= 0:
                raise ValueError(
                    f"Invalid execution time for {test}."
                )

    def coverage_of(self, selected_tests):
        """Return all code lines covered by selected tests."""

        covered_lines = set()

        for test in selected_tests:
            if test not in self.tests:
                raise ValueError(f"Unknown test: {test}")

            covered_lines.update(self.coverage[test])

        return covered_lines

    def time_of(self, selected_tests):
        """Calculate total execution time of selected tests."""

        total_time = 0

        for test in selected_tests:
            if test not in self.tests:
                raise ValueError(f"Unknown test: {test}")

            total_time += self.durations[test]

        return total_time

    def total_coverable_lines(self):
        """Return the number of unique lines covered by all tests."""

        all_lines = set()

        for lines in self.coverage.values():
            all_lines.update(lines)

        return len(all_lines)

    def summary(self):
        """Display basic information about the test suite."""

        return {
            "total_tests": len(self.tests),
            "total_execution_time": self.time_of(self.tests),
            "total_coverable_lines": self.total_coverable_lines()
        }

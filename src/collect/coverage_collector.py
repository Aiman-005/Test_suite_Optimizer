import os
import json
import subprocess
import sys
from pathlib import Path


def collect_test_coverage(project_path, test_cases):
    """Collect source-code coverage separately for every pytest test."""

    project_path = Path(project_path).resolve()

    if not project_path.is_dir():
        raise NotADirectoryError(
            f"Project directory does not exist: {project_path}"
        )

    if not test_cases:
        raise ValueError("No test cases were provided.")

    node_ids = [test["node_id"] for test in test_cases]

    if len(node_ids) != len(set(node_ids)):
        raise ValueError("Duplicate test node IDs were provided.")

    script = r'''
from pathlib import Path
import json
import sys
import coverage
import pytest


project_path = Path(sys.argv[1]).resolve()
node_ids = json.load(sys.stdin)


class TestCoveragePlugin:
    __test__ = False

    def __init__(self, coverage_tool):
        self.coverage_tool = coverage_tool

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_protocol(self, item):
        self.coverage_tool.switch_context(item.nodeid)
        yield


coverage_tool = coverage.Coverage(
    data_file=None,
    source=[str(project_path)],
    omit=[
        "*/tests/*",
        "*/.venv/*",
        "*/venv/*",
        "*/site-packages/*",
        "*/src/collect/coverage_collector.py"
    ]
)

plugin = TestCoveragePlugin(coverage_tool)

coverage_tool.start()

try:
    exit_code = pytest.main(
        [
            "-q",
            "-o", "addopts=",
            "-p", "no:cacheprovider",
            "-p", "no:cov",
            "--import-mode=importlib",
            *node_ids
        ],
        plugins=[plugin]
    )
finally:
    coverage_tool.stop()

data = coverage_tool.get_data()

test_coverage = {
    node_id: {} for node_id in node_ids
}

for source_file in data.measured_files():

    source_path = Path(source_file).resolve()

    try:
        relative_file = source_path.relative_to(
            project_path
        ).as_posix()
    except ValueError:
        continue

    lines_by_context = data.contexts_by_lineno(source_file)

    for line_number, contexts in lines_by_context.items():

        for context in contexts:

            if context in test_coverage:
                test_coverage[context].setdefault(
                    relative_file, []
                ).append(line_number)

for files in test_coverage.values():

    for source_file in files:
        files[source_file] = sorted(
            set(files[source_file])
        )

result = {
    "coverage": test_coverage,
    "pytest_exit_code": int(exit_code),
    "total_tests": len(node_ids),
    "tests_with_coverage": sum(
        bool(files) for files in test_coverage.values()
    )
}

print("COVERAGE_RESULT:" + json.dumps(result))
'''

    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(project_path)
        ],
        cwd=str(project_path),
        capture_output=True,
        text=True,
        input=json.dumps(node_ids),
        env={
            **os.environ,
            "COVERAGE_CORE": "ctrace"
        }
    )

    marker = "COVERAGE_RESULT:"

    for line in reversed(completed.stdout.splitlines()):

        if line.startswith(marker):
            result = json.loads(line[len(marker):])

            if completed.returncode != 0:
                raise RuntimeError(
                    f"Coverage subprocess failed: {completed.stderr}"
                )

            return result

    raise RuntimeError(
        "Coverage collection failed.\n"
        f"Return code: {completed.returncode}\n"
        f"Output:\n{completed.stdout}\n"
        f"Errors:\n{completed.stderr}"
    )

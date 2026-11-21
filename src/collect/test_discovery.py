
import json
import subprocess
import sys
from pathlib import Path


EXCLUDED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "collect-venv",
    "__pycache__",
    ".pytest_cache",
    "site-packages"
}


def discover_test_files(project_path):
    """Find pytest test files inside a Python project."""

    project_path = Path(project_path).resolve()

    if not project_path.exists():
        raise FileNotFoundError(
            f"Project directory does not exist: {project_path}"
        )

    if not project_path.is_dir():
        raise NotADirectoryError(
            f"Expected a project directory: {project_path}"
        )

    test_files = []

    for path in project_path.rglob("*.py"):
        if EXCLUDED_DIRECTORIES.intersection(path.parts):
            continue

        if path.name.startswith("test_") or path.name.endswith("_test.py"):
            test_files.append(path)

    return sorted(test_files)


def discover_test_cases(project_path):
    """
    Discover actual pytest test cases, including parametrized tests.

    Pytest performs collection in a separate process so this function
    can also safely be called from an existing pytest test session.
    """

    project_path = Path(project_path).resolve()

    if not project_path.exists():
        raise FileNotFoundError(
            f"Project directory does not exist: {project_path}"
        )

    if not project_path.is_dir():
        raise NotADirectoryError(
            f"Expected a project directory: {project_path}"
        )

    collection_script = r'''
import json
import sys
from pathlib import Path

import pytest


project_path = Path(sys.argv[1]).resolve()


class TestCollectionPlugin:
    __test__ = False

    def __init__(self):
        self.test_cases = []

    def pytest_collection_finish(self, session):
        for item in session.items:

            test_file = Path(str(item.path)).resolve()

            try:
                relative_path = test_file.relative_to(
                    project_path
                ).as_posix()
            except ValueError:
                continue

            test_class = getattr(item, "cls", None)

            if test_class is not None:
                name = f"{test_class.__name__}.{item.name}"
            else:
                name = item.name

            self.test_cases.append({
                "name": name,
                "file": relative_path,
                "node_id": item.nodeid
            })


plugin = TestCollectionPlugin()

exit_code = pytest.main(
    [
        "--collect-only",
        "-q",
        "-o",
        "addopts=",
        "-p",
        "no:cacheprovider",
        "--import-mode=importlib"
    ],
    plugins=[plugin]
)

print(
    "DISCOVERED_TESTS:" + json.dumps(plugin.test_cases)
)

if int(exit_code) not in (0, 5):
    sys.exit(int(exit_code))
'''

    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            collection_script,
            str(project_path)
        ],
        cwd=str(project_path),
        capture_output=True,
        text=True
    )

    marker = "DISCOVERED_TESTS:"
    discovered_tests = None

    for line in reversed(completed.stdout.splitlines()):
        if line.startswith(marker):
            discovered_tests = json.loads(
                line[len(marker):]
            )
            break

    if discovered_tests is None:
        raise RuntimeError(
            "Pytest test discovery failed.\n"
            f"Return code: {completed.returncode}\n"
            f"Output:\n{completed.stdout}\n"
            f"Errors:\n{completed.stderr}"
        )

    if completed.returncode not in (0, 5):
        raise RuntimeError(
            "Pytest encountered an error during test collection.\n"
            f"Output:\n{completed.stdout}\n"
            f"Errors:\n{completed.stderr}"
        )

    return discovered_tests

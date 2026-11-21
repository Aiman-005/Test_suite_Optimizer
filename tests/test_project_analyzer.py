
import pytest

from src.app import project_analyzer


def test_analyze_project_builds_problem_from_real_data(
    tmp_path,
    monkeypatch
):
    test_cases = [
        {
            "name": "test_one",
            "file": "tests/test_sample.py",
            "node_id": "tests/test_sample.py::test_one"
        },
        {
            "name": "test_two",
            "file": "tests/test_sample.py",
            "node_id": "tests/test_sample.py::test_two"
        }
    ]

    execution_result = {
        "results": [
            {
                "node_id": "tests/test_sample.py::test_one",
                "status": "passed",
                "duration_seconds": 0.5
            },
            {
                "node_id": "tests/test_sample.py::test_two",
                "status": "failed",
                "duration_seconds": 0.3
            }
        ],
        "pytest_exit_code": 1,
        "total_tests": 2,
        "passed": 1,
        "failed": 1,
        "skipped": 0
    }

    coverage_result = {
        "coverage": {
            "tests/test_sample.py::test_one": {
                "src/app.py": [1, 2, 3]
            },
            "tests/test_sample.py::test_two": {
                "src/app.py": [4, 5]
            }
        },
        "pytest_exit_code": 0,
        "total_tests": 2,
        "tests_with_coverage": 2
    }

    monkeypatch.setattr(
        project_analyzer,
        "discover_test_cases",
        lambda path: test_cases
    )

    monkeypatch.setattr(
        project_analyzer,
        "run_discovered_tests",
        lambda path, cases: execution_result
    )

    monkeypatch.setattr(
        project_analyzer,
        "collect_test_coverage",
        lambda path, cases: coverage_result
    )

    result = project_analyzer.analyze_project(
        tmp_path,
        budget=1.0
    )

    problem = result["problem"]

    assert result["discovered_tests"] == 2
    assert result["included_tests"] == 1
    assert len(result["excluded_tests"]) == 1

    assert problem.suite.tests == [
        "tests/test_sample.py::test_one"
    ]

    assert problem.suite.durations[
        "tests/test_sample.py::test_one"
    ] == 0.5

    assert problem.suite.coverage[
        "tests/test_sample.py::test_one"
    ] == {
        "src/app.py:1",
        "src/app.py:2",
        "src/app.py:3"
    }


def test_analyze_project_rejects_missing_directory(tmp_path):
    missing_path = tmp_path / "missing"

    with pytest.raises(FileNotFoundError):
        project_analyzer.analyze_project(
            missing_path,
            budget=5
        )


def test_analyze_project_rejects_no_discovered_tests(
    tmp_path,
    monkeypatch
):
    monkeypatch.setattr(
        project_analyzer,
        "discover_test_cases",
        lambda path: []
    )

    with pytest.raises(ValueError, match="No pytest test cases"):
        project_analyzer.analyze_project(
            tmp_path,
            budget=5
        )


def test_analyze_project_rejects_when_all_tests_fail(
    tmp_path,
    monkeypatch
):
    test_cases = [
        {
            "name": "test_failure",
            "file": "tests/test_sample.py",
            "node_id": "tests/test_sample.py::test_failure"
        }
    ]

    monkeypatch.setattr(
        project_analyzer,
        "discover_test_cases",
        lambda path: test_cases
    )

    monkeypatch.setattr(
        project_analyzer,
        "run_discovered_tests",
        lambda path, cases: {
            "results": [
                {
                    "node_id": "tests/test_sample.py::test_failure",
                    "status": "failed",
                    "duration_seconds": 0.2
                }
            ],
            "pytest_exit_code": 1,
            "total_tests": 1,
            "passed": 0,
            "failed": 1,
            "skipped": 0
        }
    )

    monkeypatch.setattr(
        project_analyzer,
        "collect_test_coverage",
        lambda path, cases: {
            "coverage": {
                "tests/test_sample.py::test_failure": {
                    "src/app.py": [1, 2]
                }
            }
        }
    )

    with pytest.raises(
        ValueError,
        match="No successfully executed tests"
    ):
        project_analyzer.analyze_project(
            tmp_path,
            budget=5
        )

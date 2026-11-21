
from src.collect.test_executor import run_discovered_tests


def test_executor_records_test_results(tmp_path, monkeypatch):
    import src.collect.test_executor as executor

    test_cases = [
        {"node_id": "tests/test_demo.py::test_demo"}
    ]

    def fake_pytest_main(args, plugins):
        plugin = plugins[0]
        plugin.statuses["tests/test_demo.py::test_demo"] = "passed"
        plugin.durations["tests/test_demo.py::test_demo"] = 0.25
        return 0

    monkeypatch.setattr(executor.pytest, "main", fake_pytest_main)

    result = run_discovered_tests(tmp_path, test_cases)

    assert result["total_tests"] == 1
    assert result["passed"] == 1
    assert result["failed"] == 0
    assert result["results"][0]["duration_seconds"] == 0.25


def test_executor_rejects_empty_test_list(tmp_path):
    import pytest

    with pytest.raises(ValueError):
        run_discovered_tests(tmp_path, [])


def test_executor_rejects_invalid_directory(tmp_path):
    import pytest

    invalid_path = tmp_path / "missing"

    with pytest.raises(NotADirectoryError):
        run_discovered_tests(invalid_path, [
            {"node_id": "test_demo.py::test_demo"}
        ])

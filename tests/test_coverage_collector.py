import json
from types import SimpleNamespace

import pytest
from src.collect import coverage_collector
from src.collect.coverage_collector import collect_test_coverage


def test_collects_coverage_for_individual_tests(tmp_path):
    (tmp_path / "app.py").write_text(
        """
def first_function():
    return 10


def second_function():
    return 20
"""
    )

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()

    (tests_dir / "test_app.py").write_text(
        """
from app import first_function, second_function


def test_first():
    assert first_function() == 10


def test_second():
    assert second_function() == 20
"""
    )

    test_cases = [
        {"node_id": "tests/test_app.py::test_first"},
        {"node_id": "tests/test_app.py::test_second"}
    ]

    result = collect_test_coverage(tmp_path, test_cases)

    assert result["pytest_exit_code"] == 0
    assert result["total_tests"] == 2
    assert result["tests_with_coverage"] == 2

    first_coverage = result["coverage"][
        "tests/test_app.py::test_first"
    ]

    second_coverage = result["coverage"][
        "tests/test_app.py::test_second"
    ]

    assert "app.py" in first_coverage
    assert "app.py" in second_coverage

    assert 3 in first_coverage["app.py"]
    assert 7 in second_coverage["app.py"]


def test_passes_large_node_id_list_via_stdin(tmp_path, monkeypatch):
    test_cases = [
        {
            "node_id": (
                f"tests/test_example.py::test_case_{index}_"
                + "x" * 50
            )
        }
        for index in range(621)
    ]
    node_ids_json = json.dumps(
        [test["node_id"] for test in test_cases]
    )

    def fake_run(args, **kwargs):
        assert len(args) == 4
        assert kwargs["input"] == node_ids_json
        assert len(node_ids_json) > 32767
        result = {
            "coverage": {},
            "pytest_exit_code": 0,
            "total_tests": len(test_cases),
            "tests_with_coverage": 0
        }
        return SimpleNamespace(
            stdout=f"COVERAGE_RESULT:{json.dumps(result)}",
            stderr="",
            returncode=0
        )

    monkeypatch.setattr(
        coverage_collector.subprocess,
        "run",
        fake_run
    )

    result = collect_test_coverage(tmp_path, test_cases)

    assert result["total_tests"] == 621


def test_rejects_empty_test_list(tmp_path):
    with pytest.raises(ValueError):
        collect_test_coverage(tmp_path, [])


def test_rejects_invalid_directory(tmp_path):
    invalid_path = tmp_path / "missing"

    with pytest.raises(NotADirectoryError):
        collect_test_coverage(
            invalid_path,
            [{"node_id": "test_demo.py::test_demo"}]
        )


def test_rejects_duplicate_node_ids(tmp_path):
    test_cases = [
        {"node_id": "test_demo.py::test_demo"},
        {"node_id": "test_demo.py::test_demo"}
    ]

    with pytest.raises(ValueError):
        collect_test_coverage(tmp_path, test_cases)

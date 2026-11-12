
import json
import pytest

from src.core.data_loader import load_problem


def create_dataset(tmp_path, data):
    """Create a temporary JSON dataset for testing."""

    file_path = tmp_path / "sample.json"

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file)

    return file_path


def test_load_valid_dataset(tmp_path):
    data = {
        "project_name": "Sample Project",
        "budget": 6,
        "tests": [
            {
                "name": "test_login",
                "duration": 2,
                "coverage": [1, 2, 3]
            },
            {
                "name": "test_signup",
                "duration": 3,
                "coverage": [2, 3, 4]
            }
        ]
    }

    file_path = create_dataset(tmp_path, data)

    problem = load_problem(file_path)

    assert problem.budget == 6
    assert problem.suite.tests == ["test_login", "test_signup"]
    assert problem.suite.total_coverable_lines() == 4


def test_load_dataset_with_missing_fields(tmp_path):
    data = {
        "project_name": "Sample Project",
        "tests": []
    }

    file_path = create_dataset(tmp_path, data)

    with pytest.raises(ValueError):
        load_problem(file_path)


def test_load_dataset_with_duplicate_tests(tmp_path):
    data = {
        "project_name": "Sample Project",
        "budget": 6,
        "tests": [
            {
                "name": "test_login",
                "duration": 2,
                "coverage": [1, 2]
            },
            {
                "name": "test_login",
                "duration": 3,
                "coverage": [3, 4]
            }
        ]
    }

    file_path = create_dataset(tmp_path, data)

    with pytest.raises(ValueError):
        load_problem(file_path)


def test_load_dataset_with_invalid_duration(tmp_path):
    data = {
        "project_name": "Sample Project",
        "budget": 6,
        "tests": [
            {
                "name": "test_login",
                "duration": -2,
                "coverage": [1, 2]
            }
        ]
    }

    file_path = create_dataset(tmp_path, data)

    with pytest.raises(ValueError):
        load_problem(file_path)

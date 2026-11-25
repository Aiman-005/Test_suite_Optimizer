
from src.collect.test_discovery import (
    discover_test_files,
    discover_test_cases
)
def test_discover_test_files(tmp_path):
    (tmp_path / "tests").mkdir()

    (tmp_path / "tests" / "test_login.py").write_text(
        "def test_login():\n    assert True\n"
    )

    (tmp_path / "tests" / "user_test.py").write_text(
        "def test_user():\n    assert True\n"
    )

    (tmp_path / "tests" / "helper.py").write_text(
        "def helper():\n    pass\n"
    )

    files = discover_test_files(tmp_path)

    assert len(files) == 2


def test_discover_test_cases(tmp_path):
    (tmp_path / "tests").mkdir()

    (tmp_path / "tests" / "test_sample.py").write_text(
        """
def test_first():
    assert True


class TestExample:
    def test_second(self):
        assert True
"""
    )

    discovered = discover_test_cases(tmp_path)

    assert len(discovered) == 2
    assert discovered[0]["name"] == "test_first"
    assert discovered[1]["name"] == "TestExample.test_second"


def test_discover_test_cases_returns_node_ids(tmp_path):
    (tmp_path / "tests").mkdir()

    (tmp_path / "tests" / "test_demo.py").write_text(
        "def test_demo():\n    assert True\n"
    )

    discovered = discover_test_cases(tmp_path)

    assert discovered[0]["node_id"] == "tests/test_demo.py::test_demo"

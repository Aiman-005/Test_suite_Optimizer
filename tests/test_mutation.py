import ast

from src.collect.mutation import find_mutation_points, run_mutants

SOURCE = '''def check(a, b, items):
    if a < b and not items:
        return a + 1
    if a is None or b in items:
        return True
    return a * b != 0
'''


def test_mutation_points_cover_each_operator_and_stay_valid_python():
    points = find_mutation_points(SOURCE, set(range(1, 7)))
    operators = {operator for _, operator, _, _, _ in points}

    assert {"arithmetic", "comparison", "logical", "negation", "constant"} <= operators

    lines = SOURCE.splitlines()
    for line, _, _, _, new_line in points:
        mutated = lines.copy()
        mutated[line - 1] = new_line
        ast.parse("\n".join(mutated))  # every mutant must still be valid Python


def test_only_covered_lines_are_mutated():
    points = find_mutation_points(SOURCE, {3})
    assert points and all(line == 3 for line, *_ in points)


def test_run_mutants_records_which_tests_catch_each_bug(tmp_path):
    project = tmp_path / "demo"
    (project / "demo").mkdir(parents=True)
    (project / "tests").mkdir()
    (project / "demo" / "__init__.py").write_text("")
    (project / "demo" / "calc.py").write_text("def add(a, b):\n    return a + b\n")
    (project / "tests" / "test_calc.py").write_text(
        "from demo.calc import add\n\n"
        "def test_add():\n    assert add(2, 3) == 5\n\n"
        "def test_zero():\n    assert add(0, 0) == 0\n"
    )

    mutant = {
        "mutant_id": "M000", "file": "demo/calc.py", "line": 2,
        "operator": "arithmetic", "original": "+", "replacement": "-",
        "new_line": "    return a - b",
    }
    tests_by_line = {("demo/calc.py", 2): [
        "tests/test_calc.py::test_add", "tests/test_calc.py::test_zero",
    ]}

    kills, passing = run_mutants(project, [mutant], tests_by_line, log=lambda *_: None)

    assert len(passing) == 2
    # a - b is wrong for (2, 3) but still right for (0, 0).
    assert kills["M000"] == {"tests/test_calc.py::test_add"}
    # The original project file is left untouched.
    assert "a + b" in (project / "demo" / "calc.py").read_text()

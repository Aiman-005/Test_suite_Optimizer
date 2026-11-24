"""
Mutation testing: seed small bugs and record which tests catch them.

A mutant is a copy of the project with one small change on a line that
at least one test covers, for example `<` -> `<=`, `+` -> `-`,
`and` -> `or`, `True` -> `False`, `n` -> `n + 1`, or removing a `not`.
For every mutant, the tests that cover the mutated line are run against
the mutated code; a test "kills" the mutant if it fails (or the run
times out). Tests that do not cover the line cannot reach the change,
so they are not run.

The result is a kill matrix (mutant x test), used to measure how many
seeded bugs a selected subset of tests still detects.
"""

import ast
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

BINARY_SWAPS = {
    ast.Add: (ast.Sub, "+", "-"),
    ast.Sub: (ast.Add, "-", "+"),
    ast.Mult: (ast.FloorDiv, "*", "//"),
    ast.FloorDiv: (ast.Mult, "//", "*"),
    ast.Div: (ast.Mult, "/", "*"),
    ast.Mod: (ast.FloorDiv, "%", "//"),
}

COMPARE_SWAPS = {
    ast.Lt: ("<", "<="),
    ast.LtE: ("<=", "<"),
    ast.Gt: (">", ">="),
    ast.GtE: (">=", ">"),
    ast.Eq: ("==", "!="),
    ast.NotEq: ("!=", "=="),
}

WORD_COMPARE_SWAPS = {
    ast.Is: ("is", "is not"),
    ast.IsNot: ("is not", "is"),
    ast.In: ("in", "not in"),
    ast.NotIn: ("not in", "in"),
}

RUNNER = r'''
import json
import sys

import pytest

node_ids = json.loads(sys.argv[1])


class OutcomePlugin:
    __test__ = False

    def __init__(self):
        self.failed = set()
        self.seen = set()

    def pytest_runtest_logreport(self, report):
        self.seen.add(report.nodeid)
        if report.failed:
            self.failed.add(report.nodeid)


plugin = OutcomePlugin()
pytest.main(["-q", "-o", "addopts=", "-p", "no:cacheprovider", *node_ids], plugins=[plugin])
print("MUTATION_RESULT:" + json.dumps({
    "failed": sorted(plugin.failed),
    "seen": sorted(plugin.seen),
}))
'''


# --------------------------------------------------------------- helpers

def _byte_slice_replace(line, start, end, old, new):
    """Replace `old` with `new` inside byte columns [start, end) of a line."""

    data = line.encode("utf-8")
    segment = data[start:end].decode("utf-8")
    index = segment.find(old)

    if index == -1:
        return None

    segment = segment[:index] + new + segment[index + len(old):]
    return (data[:start] + segment.encode("utf-8") + data[end:]).decode("utf-8")


def _find_word(segment, word):
    """Find `word` as a whole word (for and / or / is / in / not)."""

    position = 0
    while True:
        index = segment.find(word, position)
        if index == -1:
            return -1
        before = segment[index - 1] if index > 0 else " "
        after_index = index + len(word)
        after = segment[after_index] if after_index < len(segment) else " "
        if not (before.isalnum() or before == "_") and not (after.isalnum() or after == "_"):
            return index
        position = index + 1


def _replace_word(line, start, end, old, new):
    data = line.encode("utf-8")
    segment = data[start:end].decode("utf-8")
    index = _find_word(segment, old)

    if index == -1:
        return None

    segment = segment[:index] + new + segment[index + len(old):]
    return (data[:start] + segment.encode("utf-8") + data[end:]).decode("utf-8")


# ------------------------------------------------------- mutant creation

def find_mutation_points(source, covered_lines):
    """
    Return candidate mutations on covered lines of one source file.

    Each candidate is (line_number, operator, original, replacement, new_line).
    Only changes that stay on one physical line are used.
    """

    tree = ast.parse(source)
    lines = source.splitlines()
    candidates = []

    def add(node_line, operator, original, replacement, new_line):
        if new_line is not None and new_line != lines[node_line - 1]:
            candidates.append((node_line, operator, original, replacement, new_line))

    for node in ast.walk(tree):
        lineno = getattr(node, "lineno", None)
        if lineno is None or lineno not in covered_lines:
            continue

        line = lines[lineno - 1]

        if isinstance(node, ast.BinOp) and type(node.op) in BINARY_SWAPS:
            if node.left.end_lineno == node.right.lineno == lineno:
                _, old, new = BINARY_SWAPS[type(node.op)]
                new_line = _byte_slice_replace(
                    line, node.left.end_col_offset, node.right.col_offset, old, new
                )
                add(lineno, "arithmetic", old, new, new_line)

        elif isinstance(node, ast.Compare) and len(node.ops) == 1:
            right = node.comparators[0]
            if node.left.end_lineno == right.lineno == lineno:
                op_type = type(node.ops[0])
                start, end = node.left.end_col_offset, right.col_offset
                if op_type in COMPARE_SWAPS:
                    old, new = COMPARE_SWAPS[op_type]
                    add(lineno, "comparison", old, new,
                        _byte_slice_replace(line, start, end, old, new))
                elif op_type in WORD_COMPARE_SWAPS:
                    old, new = WORD_COMPARE_SWAPS[op_type]
                    if op_type in (ast.IsNot, ast.NotIn):
                        new_line = _byte_slice_replace(line, start, end, old, new)
                    else:
                        new_line = _replace_word(line, start, end, old, new)
                    add(lineno, "comparison", old, new, new_line)

        elif isinstance(node, ast.BoolOp) and len(node.values) >= 2:
            first, second = node.values[0], node.values[1]
            if first.end_lineno == second.lineno == lineno:
                old, new = ("and", "or") if isinstance(node.op, ast.And) else ("or", "and")
                add(lineno, "logical", old, new,
                    _replace_word(line, first.end_col_offset, second.col_offset, old, new))

        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            if node.operand.lineno == lineno:
                new_line = _replace_word(line, node.col_offset, node.operand.col_offset, "not", "")
                if new_line is not None:
                    data = new_line.encode("utf-8")
                    # Remove the space left behind after "not".
                    start = node.col_offset
                    if data[start:start + 1] == b" ":
                        new_line = (data[:start] + data[start + 1:]).decode("utf-8")
                add(lineno, "negation", "not", "", new_line)

        elif isinstance(node, ast.Constant) and node.end_lineno == lineno:
            if node.value is True or node.value is False:
                old = "True" if node.value else "False"
                new = "False" if node.value else "True"
                add(lineno, "constant", old, new,
                    _byte_slice_replace(line, node.col_offset, node.end_col_offset, old, new))
            elif type(node.value) is int:
                data = line.encode("utf-8")
                literal = data[node.col_offset:node.end_col_offset].decode("utf-8")
                if literal.isdigit():
                    new = str(node.value + 1)
                    add(lineno, "constant", literal, new,
                        _byte_slice_replace(line, node.col_offset, node.end_col_offset, literal, new))

    return candidates


def generate_mutants(project_path, covered_by_file, max_mutants=150, seed=0):
    """Sample up to max_mutants mutants spread over the covered source files."""

    project_path = Path(project_path)
    pool = []

    for source_file, covered in sorted(covered_by_file.items()):
        path = project_path / source_file
        if not path.is_file():
            continue

        source = path.read_text(encoding="utf-8")
        try:
            points = find_mutation_points(source, covered)
        except SyntaxError:
            continue

        for line, operator, original, replacement, new_line in points:
            pool.append({
                "file": source_file,
                "line": line,
                "operator": operator,
                "original": original,
                "replacement": replacement,
                "new_line": new_line,
            })

    # Remove exact duplicates (same file, line and resulting text).
    unique = {(m["file"], m["line"], m["new_line"]): m for m in pool}
    pool = sorted(unique.values(), key=lambda m: (m["file"], m["line"], m["new_line"]))

    rng = random.Random(seed)
    sample = rng.sample(pool, min(max_mutants, len(pool)))
    sample.sort(key=lambda m: (m["file"], m["line"]))

    for index, mutant in enumerate(sample):
        mutant["mutant_id"] = f"M{index:03d}"

    return sample, len(pool)


# --------------------------------------------------------- mutant running

def _run_tests(workdir, node_ids, timeout):
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}

    try:
        completed = subprocess.run(
            [sys.executable, "-c", RUNNER, json.dumps(node_ids)],
            cwd=str(workdir), capture_output=True, text=True,
            timeout=timeout, env=env,
        )
    except subprocess.TimeoutExpired:
        return None  # an endless loop: every test that was run catches it

    for line in reversed(completed.stdout.splitlines()):
        if line.startswith("MUTATION_RESULT:"):
            return json.loads(line[len("MUTATION_RESULT:"):])

    # Pytest could not even start (e.g. the mutant breaks an import):
    # every test that was meant to run catches it.
    return {"failed": list(node_ids), "seen": list(node_ids)}


def run_mutants(project_path, mutants, tests_by_line, timeout=60, log=print):
    """
    Run each mutant against the tests covering its line.

    tests_by_line: {(source_file, line): [test node ids]}
    Returns (kills, passing_tests): kills = {mutant_id: set(test ids)}.
    """

    project_path = Path(project_path).resolve()
    temp_root = Path(tempfile.mkdtemp(prefix="tso_mutation_"))
    workdir = temp_root / project_path.name

    shutil.copytree(
        project_path, workdir,
        ignore=shutil.ignore_patterns(".git", ".venv", "venv", "__pycache__",
                                      ".pytest_cache", ".coverage", "*.pyc"),
    )

    try:
        all_tests = sorted({t for tests in tests_by_line.values() for t in tests})
        baseline = _run_tests(workdir, all_tests, timeout=timeout * 10)
        broken = set(baseline["failed"]) if baseline else set()
        passing = [t for t in all_tests if t not in broken]
        log(f"Baseline: {len(passing)} of {len(all_tests)} covering tests pass unmutated")

        kills = {}

        for number, mutant in enumerate(mutants, 1):
            target = workdir / mutant["file"]
            original_source = target.read_text(encoding="utf-8")
            lines = original_source.splitlines(keepends=True)
            ending = "\n" if lines[mutant["line"] - 1].endswith("\n") else ""
            lines[mutant["line"] - 1] = mutant["new_line"] + ending

            tests = [
                t for t in tests_by_line.get((mutant["file"], mutant["line"]), [])
                if t not in broken
            ]

            if not tests:
                kills[mutant["mutant_id"]] = set()
                continue

            target.write_text("".join(lines), encoding="utf-8")
            try:
                result = _run_tests(workdir, tests, timeout)
            finally:
                target.write_text(original_source, encoding="utf-8")

            if result is None:
                killed = set(tests)
            else:
                killed = set(result["failed"]) & set(tests)

            kills[mutant["mutant_id"]] = killed

            if number % 10 == 0 or number == len(mutants):
                done = sum(1 for k in kills.values() if k)
                log(f"  {number}/{len(mutants)} mutants run, {done} caught so far")

        return kills, passing

    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def load_coverage(coverage_csv):
    """Read a coverage matrix into {file: set(lines)} and {(file, line): [tests]}."""

    import csv

    covered_by_file = defaultdict(set)
    tests_by_line = defaultdict(list)

    with Path(coverage_csv).open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            for value in row["covered_lines"].split(";"):
                if value:
                    line = int(value)
                    covered_by_file[row["source_file"]].add(line)
                    tests_by_line[(row["source_file"], line)].append(row["test_node_id"])

    return covered_by_file, tests_by_line

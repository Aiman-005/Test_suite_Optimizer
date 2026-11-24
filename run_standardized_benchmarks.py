import csv
import time
from pathlib import Path

from src.core.test_suite import TestSuite
from src.core.selection_problem import SelectionProblem

from src.algorithms.random_selection import RandomSelectionOptimizer
from src.algorithms.greedy import GreedyOptimizer
from src.algorithms.hill_climbing import HillClimbingOptimizer
from src.algorithms.simulated_annealing import SimulatedAnnealingOptimizer


PROJECTS = {
    "TinyDB": {
        "estimates": "data/processed/tinydb_kalman_estimates.csv",
        "coverage": "data/processed/tinydb_coverage_matrix.csv",
        "id_column": "test_node_id",
        "duration_column": "kalman_estimate_seconds",
        "budget": 0.24
    },
    "Toolz": {
        "estimates": "data/processed/toolz_kalman_estimates.csv",
        "coverage": "data/processed/toolz_coverage_matrix.csv",
        "id_column": "test_node_id",
        "duration_column": "kalman_estimate_seconds",
        "budget": 0.452752
    },
    "Boltons": {
        "estimates": "data/processed/boltons_kalman_estimates.csv",
        "coverage": "data/processed/boltons_coverage_matrix.csv",
        "id_column": "node_id",
        "duration_column": "estimated_duration",
        "budget": 1.8701
    }
}


def build_problem(config):
    durations = {}

    with Path(config["estimates"]).open(
        newline="", encoding="utf-8"
    ) as file:
        for row in csv.DictReader(file):
            node_id = row[config["id_column"]]
            duration = float(row[config["duration_column"]])

            if duration > 0:
                durations[node_id] = duration

    coverage = {node_id: set() for node_id in durations}

    with Path(config["coverage"]).open(
        newline="", encoding="utf-8"
    ) as file:
        for row in csv.DictReader(file):
            node_id = row["test_node_id"]

            if node_id not in coverage:
                continue

            source_file = row["source_file"]

            for line in row["covered_lines"].split(";"):
                if line:
                    coverage[node_id].add(f"{source_file}:{line}")

    tests = list(durations)

    suite = TestSuite(tests, durations, coverage)
    problem = SelectionProblem(suite, config["budget"])

    return problem


all_results = []

for project, config in PROJECTS.items():

    print(f"\n{'=' * 55}")
    print(f"PROJECT: {project}")
    print(f"{'=' * 55}")

    problem = build_problem(config)

    print("Tests:", len(problem.suite.tests))
    print("Tests with coverage:", sum(
        bool(lines) for lines in problem.suite.coverage.values()
    ))
    print("Coverable lines:", problem.suite.total_coverable_lines())
    print("Budget:", problem.budget)

    optimizers = [
        (
            "Random Selection",
            RandomSelectionOptimizer(problem, seed=42)
        ),
        (
            "Greedy",
            GreedyOptimizer(problem)
        ),
        (
            "Hill Climbing",
            HillClimbingOptimizer(
                problem,
                max_restarts=1,
                max_neighbors=20,
                max_steps=20,
                seed=42
            )
        ),
        (
            "Simulated Annealing",
            SimulatedAnnealingOptimizer(
                problem,
                initial_temperature=100,
                cooling_rate=0.95,
                iterations=300,
                seed=42
            )
        )
    ]

    for name, optimizer in optimizers:

        start = time.perf_counter()
        selected = optimizer.optimize()
        runtime = time.perf_counter() - start

        evaluation = problem.evaluate(selected)

        record = {
            "project": project,
            "optimizer": name,
            "selected_tests": len(selected),
            "selected_execution_time": evaluation["total_time"],
            "coverage_percentage": evaluation["coverage_percentage"],
            "feasible": evaluation["feasible"],
            "optimizer_runtime_seconds": runtime,
            "budget_seconds": problem.budget
        }

        all_results.append(record)

        print(
            f"{name}: {len(selected)} tests | "
            f"Coverage: {evaluation['coverage_percentage']:.2f}% | "
            f"Time: {evaluation['total_time']:.4f}s | "
            f"Runtime: {runtime:.4f}s | "
            f"Feasible: {evaluation['feasible']}"
        )


fields = [
    "project",
    "optimizer",
    "selected_tests",
    "selected_execution_time",
    "coverage_percentage",
    "feasible",
    "optimizer_runtime_seconds",
    "budget_seconds"
]

for project in PROJECTS:
    output = Path(
        f"results/{project.lower()}_benchmark_standardized.csv"
    )

    project_results = [
        row for row in all_results
        if row["project"] == project
    ]

    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(project_results)

    print(f"\nSaved {project} benchmark to: {output}")

print("\nAll projects benchmarked.")
print("Total records:", len(all_results))

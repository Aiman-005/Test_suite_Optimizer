import csv
import time
from pathlib import Path

from src.core.test_suite import TestSuite
from src.core.selection_problem import SelectionProblem

from src.algorithms.random_selection import RandomSelectionOptimizer
from src.algorithms.greedy import GreedyOptimizer
from src.algorithms.hill_climbing import HillClimbingOptimizer
from src.algorithms.simulated_annealing import SimulatedAnnealingOptimizer


estimates_path = Path("data/processed/boltons_kalman_estimates.csv")
coverage_path = Path("data/processed/boltons_coverage_matrix.csv")
output_path = Path("results/boltons_benchmark.csv")

durations = {}
coverage = {}

with estimates_path.open(newline="", encoding="utf-8") as file:
    for row in csv.DictReader(file):
        node_id = row["node_id"]
        durations[node_id] = float(row["estimated_duration"])
        coverage[node_id] = set()

with coverage_path.open(newline="", encoding="utf-8") as file:
    for row in csv.DictReader(file):
        node_id = row["test_node_id"]
        if node_id in coverage:
            source_file = row["source_file"]
            lines = row["covered_lines"].split(";")
            for line in lines:
                if line:
                    coverage[node_id].add(f"{source_file}:{line}")

tests = list(durations.keys())

suite = TestSuite(tests, durations, coverage)

total_suite_time = suite.time_of(tests)
budget = total_suite_time * 0.5

problem = SelectionProblem(suite, budget)

print("Boltons optimization problem built.")
print("Tests:", len(tests))
print("Tests with coverage:", sum(bool(v) for v in coverage.values()))
print("Total coverable lines:", suite.total_coverable_lines())
print("Total estimated suite time:", round(total_suite_time, 4))
print("50% time budget:", round(budget, 4))

optimizers = [
    ("Random Selection", RandomSelectionOptimizer(problem, seed=42)),
    ("Greedy", GreedyOptimizer(problem)),
    ("Hill Climbing", HillClimbingOptimizer(problem, seed=42)),
    ("Simulated Annealing", SimulatedAnnealingOptimizer(problem, seed=42))
]

results = []

for name, optimizer in optimizers:
    start = time.perf_counter()
    selected = optimizer.optimize()
    runtime = time.perf_counter() - start

    evaluation = problem.evaluate(selected)

    results.append({
        "optimizer": name,
        "selected_tests": len(selected),
        "selected_execution_time": evaluation["total_time"],
        "coverage_percentage": evaluation["coverage_percentage"],
        "feasible": evaluation["feasible"],
        "optimizer_runtime_seconds": runtime
    })

    print(
        f"{name}: {len(selected)} tests | "
        f"Coverage: {evaluation['coverage_percentage']:.2f}% | "
        f"Time: {evaluation['total_time']:.4f}s | "
        f"Feasible: {evaluation['feasible']} | "
        f"Optimizer runtime: {runtime:.4f}s"
    )

output_path.parent.mkdir(parents=True, exist_ok=True)

with output_path.open("w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)

print("\nBenchmark saved to:", output_path)

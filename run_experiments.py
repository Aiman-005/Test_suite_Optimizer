"""
Reproduce benchmark records and charts with one command.
Reads only data/processed/. Writes:
  results/combined_benchmark.csv      main benchmark: 50% budget, seed 42, including UCS (20,000-state limit)
  results/budget_sweep.csv            four heuristic methods x project x budget x seed
  results/budget_sweep_summary.csv    mean and standard deviation over seeds
  results/exact_small_instances.csv   30 small sub-suites: optimum, UCS/A* nodes, CSP backtracks
  results/convergence.csv             best coverage per iteration (hill climbing, simulated annealing)
  results/kalman_evaluation.csv       single run vs mean vs Kalman, and budget overruns on held-out runs
  (bug detection uses data/processed/<project>_kill_matrix.csv from collect_mutants.py)
  results/charts/*.png
"""

import argparse
import csv
import itertools
import random
import statistics
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.core.test_suite import TestSuite
from src.core.selection_problem import SelectionProblem
from src.core.kalman_filter import KalmanDurationEstimator
from src.algorithms.random_selection import RandomSelectionOptimizer
from src.algorithms.greedy import GreedyOptimizer
from src.algorithms.hill_climbing import HillClimbingOptimizer
from src.algorithms.simulated_annealing import SimulatedAnnealingOptimizer
from src.algorithms.search_optimization import SearchOptimizer, UniformCostSearch, AStarSearch
from src.algorithms.csp_optimizer import CSPOptimizer
from src.evaluation.visualization import create_comparison_charts

PROJECTS = {"TinyDB": "tinydb", "Toolz": "toolz", "Boltons": "boltons"}
BUDGETS = [0.01, 0.02, 0.05, 0.10, 0.30, 0.50, 0.70]
DATA_DIR = Path("data/processed")
RESULTS_DIR = Path("results")
CHARTS_DIR = RESULTS_DIR / "charts"
METHODS = ["Random Selection", "Greedy", "Hill Climbing", "Simulated Annealing"]
MAIN_BENCHMARK_METHODS = METHODS + ["Uniform-Cost Search"]


# ----------------------------------------------------------------- data

def load_project(key):
    durations = {}
    with (DATA_DIR / f"{key}_kalman_estimates.csv").open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            value = float(row["kalman_estimate_seconds"])
            if value > 0:
                durations[row["test_node_id"]] = value

    coverage = {test: set() for test in durations}
    with (DATA_DIR / f"{key}_coverage_matrix.csv").open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            if row["test_node_id"] in coverage:
                for line in row["covered_lines"].split(";"):
                    if line:
                        coverage[row["test_node_id"]].add(f'{row["source_file"]}:{line}')

    tests = list(durations)
    return TestSuite(tests, durations, coverage)


def load_kill_matrix(key):
    """Return ({test: set(mutants it catches)}, set(mutants caught by the full suite))."""

    path = DATA_DIR / f"{key}_kill_matrix.csv"
    kills_by_test = {}

    if not path.exists():
        return kills_by_test, set()

    with path.open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            kills_by_test.setdefault(row["test_node_id"], set()).add(row["mutant_id"])

    detectable = set().union(*kills_by_test.values()) if kills_by_test else set()
    return kills_by_test, detectable


def mutation_score(selected, kill_data):
    """% of the bugs the full suite catches that the selected tests still catch."""

    kills_by_test, detectable = kill_data
    if not detectable:
        return None

    caught = set()
    for test in selected:
        caught |= kills_by_test.get(test, set())

    return 100 * len(caught & detectable) / len(detectable)


def make_optimizer(name, problem, seed):
    if name == "Random Selection":
        return RandomSelectionOptimizer(problem, seed=seed)
    if name == "Greedy":
        return GreedyOptimizer(problem)
    if name == "Hill Climbing":
        return HillClimbingOptimizer(problem, seed=seed)
    if name == "Simulated Annealing":
        return SimulatedAnnealingOptimizer(problem, seed=seed)
    if name == "Uniform-Cost Search":
        return SearchOptimizer(problem)
    raise ValueError(f"Unsupported benchmark method: {name}")


def run_method(name, problem, seed):
    optimizer = make_optimizer(name, problem, seed)
    start = time.perf_counter()
    if name == "Uniform-Cost Search":
        selected = optimizer.uniform_cost_search()
    else:
        selected = optimizer.optimize()
    runtime = time.perf_counter() - start
    result = problem.evaluate(selected)
    result["optimizer_runtime_seconds"] = runtime
    result["history"] = getattr(optimizer, "history", None)
    if name == "Uniform-Cost Search":
        result["nodes_expanded"] = optimizer.nodes_expanded
        result["state_limit"] = optimizer.max_states
        result["state_limit_reached"] = optimizer.state_limit_reached
        result["optimality_proven"] = not optimizer.state_limit_reached
    return result


# ------------------------------------------------------- experiments

def main_benchmark(suites, kill_data):
    rows = []
    for project, suite in suites.items():
        problem = SelectionProblem(suite, suite.time_of(suite.tests) * 0.5)
        for name in MAIN_BENCHMARK_METHODS:
            r = run_method(name, problem, seed=42)
            rows.append({
                "project": project,
                "optimizer": name,
                "selected_tests": len(r["selected_tests"]),
                "selected_execution_time": r["total_time"],
                "coverage_percentage": r["coverage_percentage"],
                "feasible": r["feasible"],
                "optimizer_runtime_seconds": r["optimizer_runtime_seconds"],
                "budget_seconds": problem.budget,
                "mutants_caught_percentage": mutation_score(r["selected_tests"], kill_data[project]),
                "nodes_expanded": r.get("nodes_expanded"),
                "state_limit": r.get("state_limit"),
                "state_limit_reached": r.get("state_limit_reached"),
                "optimality_proven": r.get("optimality_proven"),
            })
    pd.DataFrame(rows).to_csv(RESULTS_DIR / "combined_benchmark.csv", index=False)
    print("Main benchmark saved.")


def budget_sweep(suites, seeds, kill_data):
    rows, convergence = [], []
    for project, suite in suites.items():
        total = suite.time_of(suite.tests)
        for fraction in BUDGETS:
            problem = SelectionProblem(suite, total * fraction)
            for name in METHODS:
                run_seeds = [0] if name == "Greedy" else range(seeds)
                for seed in run_seeds:
                    r = run_method(name, problem, seed)
                    rows.append({
                        "project": project, "budget_fraction": fraction,
                        "optimizer": name, "seed": seed,
                        "coverage_percentage": r["coverage_percentage"],
                        "mutants_caught_percentage": mutation_score(r["selected_tests"], kill_data[project]),
                        "selected_tests": len(r["selected_tests"]),
                        "selected_execution_time": r["total_time"],
                        "feasible": r["feasible"],
                        "optimizer_runtime_seconds": r["optimizer_runtime_seconds"],
                    })
                    if fraction == 0.05 and seed == 0 and r["history"]:
                        for step, value in enumerate(r["history"]):
                            convergence.append({
                                "project": project, "optimizer": name,
                                "iteration": step, "best_coverage": value,
                            })
            print(f"  {project} at {fraction:.0%} budget done")

    sweep = pd.DataFrame(rows)
    sweep.to_csv(RESULTS_DIR / "budget_sweep.csv", index=False)
    summary = (
        sweep.groupby(["project", "budget_fraction", "optimizer"])
        .agg(mean_coverage=("coverage_percentage", "mean"),
             std_coverage=("coverage_percentage", "std"),
             best_coverage=("coverage_percentage", "max"),
             mean_mutants_caught=("mutants_caught_percentage", "mean"),
             std_mutants_caught=("mutants_caught_percentage", "std"),
             mean_runtime_seconds=("optimizer_runtime_seconds", "mean"),
             runs=("seed", "count"))
        .reset_index()
    )
    summary["std_coverage"] = summary["std_coverage"].fillna(0.0)
    summary["std_mutants_caught"] = summary["std_mutants_caught"].fillna(0.0)
    summary.to_csv(RESULTS_DIR / "budget_sweep_summary.csv", index=False)
    pd.DataFrame(convergence).to_csv(RESULTS_DIR / "convergence.csv", index=False)
    print("Budget sweep saved.")
    return summary, pd.DataFrame(convergence)


def brute_force(problem):
    tests = problem.suite.tests
    best = (-1, float("inf"))
    for mask in range(1 << len(tests)):
        chosen = [t for i, t in enumerate(tests) if mask >> i & 1]
        cost = problem.suite.time_of(chosen)
        if cost <= problem.budget:
            lines = len(problem.suite.coverage_of(chosen))
            if (lines, -cost) > (best[0], -best[1]):
                best = (lines, cost)
    return best[0]


def exact_small_instances(suites, size=15, per_project=10, budget_fraction=0.3):
    rows = []
    for project, suite in suites.items():
        pool = [t for t in suite.tests if suite.coverage[t]]
        for seed in range(per_project):
            sample = random.Random(seed).sample(pool, size)
            sub = TestSuite(sample, {t: suite.durations[t] for t in sample},
                            {t: suite.coverage[t] for t in sample})
            problem = SelectionProblem(sub, sub.time_of(sample) * budget_fraction)
            optimum = brute_force(problem)
            row = {"project": project, "instance_seed": seed, "tests": size,
                   "optimum_lines": optimum}

            def record(label, selected, runtime):
                lines = len(sub.coverage_of(selected))
                row[f"{label}_lines"] = lines
                row[f"{label}_gap_pct"] = 100 * (optimum - lines) / optimum if optimum else 0.0
                row[f"{label}_runtime_ms"] = runtime * 1000
                row[f"{label}_feasible"] = problem.is_feasible(selected)

            for label, use_heuristic in [("UCS", False), ("AStar", True)]:
                solver = SearchOptimizer(problem)
                start = time.perf_counter()
                selected = solver._search(use_heuristic=use_heuristic)
                record(label, selected, time.perf_counter() - start)
                row[f"{label}_nodes_expanded"] = solver.nodes_expanded
                row[f"{label}_nodes_generated"] = solver.nodes_generated

            # Proposal 3.3 formulation: cheapest selection covering every line.
            for label, solver_class in [("UCS", UniformCostSearch), ("AStar", AStarSearch)]:
                search = solver_class(sub)
                start = time.perf_counter()
                chosen = search.search()
                row[f"fullcover_{label}_cost_s"] = search.cost
                row[f"fullcover_{label}_nodes_expanded"] = search.nodes_expanded
                row[f"fullcover_{label}_runtime_ms"] = (time.perf_counter() - start) * 1000
                row[f"fullcover_{label}_tests"] = len(chosen) if chosen else None

            for label, mrv, fc in [("CSP_plain", False, False), ("CSP_MRV_FC", True, True)]:
                solver = CSPOptimizer(problem, use_mrv=mrv, forward_checking=fc)
                start = time.perf_counter()
                selected = solver.optimize()
                record(label, selected, time.perf_counter() - start)
                row[f"{label}_nodes"] = solver.nodes
                row[f"{label}_backtracks"] = solver.backtracks

            for name in METHODS:
                r = run_method(name, problem, seed)
                record(name.replace(" ", "_"), r["selected_tests"], r["optimizer_runtime_seconds"])

            rows.append(row)
    table = pd.DataFrame(rows)
    table.to_csv(RESULTS_DIR / "exact_small_instances.csv", index=False)
    print("Exact small-instance experiment saved.")
    return table


def kalman_evaluation(suites, budget_fraction=0.3, selections=10):
    """
    Accuracy of duration estimates built from runs 1-5, checked on runs 6-10.

    MAE: estimate vs the mean of runs 6-10.
    Selection time error: |predicted total time of a selection - its mean
    total time over runs 6-10| as a % of the latter.
    Overruns: random selections that fill the budget according to each
    estimate are re-timed on every held-out run; an overrun is a run in
    which the selected tests take longer than the budget.
    """

    rows = []
    for project, key in PROJECTS.items():
        runs = pd.read_csv(DATA_DIR / f"{key}_timing_runs.csv")
        runs = runs[runs["status"] == "passed"]
        table = runs.pivot_table(index="node_id", columns="run_number",
                                 values="duration_seconds").dropna()
        history, future = table[[1, 2, 3, 4, 5]], table[[6, 7, 8, 9, 10]]

        estimates = {
            "Single run": history[1],
            "Mean of 5 runs": history.mean(axis=1),
            "Kalman filter": pd.Series(
                [KalmanDurationEstimator().estimate_duration(list(v)) for v in history.values],
                index=history.index),
        }
        target = future.mean(axis=1)
        suite = suites[project]
        tests = [t for t in history.index if t in suite.coverage]
        budget = float(target[tests].sum()) * budget_fraction

        for name, estimate in estimates.items():
            sub = TestSuite(tests, {t: float(estimate[t]) for t in tests},
                            {t: suite.coverage[t] for t in tests})
            problem = SelectionProblem(sub, budget)
            checks = overruns = 0
            overrun_pct, time_error_pct = [], []

            for seed in range(selections):
                selected = RandomSelectionOptimizer(problem, seed=seed).optimize()
                predicted = sub.time_of(selected)
                expected = float(target[selected].sum())
                time_error_pct.append(100 * abs(predicted - expected) / expected)
                for run in future.columns:
                    actual = float(future.loc[selected, run].sum())
                    checks += 1
                    if actual > budget:
                        overruns += 1
                        overrun_pct.append(100 * (actual - budget) / budget)

            rows.append({
                "project": project, "estimate": name,
                "mae_ms": (estimate - target).abs().mean() * 1000,
                "budget_seconds": budget,
                "heldout_checks": checks,
                "heldout_overruns": overruns,
                "overrun_rate_pct": 100 * overruns / checks,
                "mean_overrun_pct": statistics.mean(overrun_pct) if overrun_pct else 0.0,
                "selection_time_error_pct": statistics.mean(time_error_pct),
            })
    table = pd.DataFrame(rows)
    table.to_csv(RESULTS_DIR / "kalman_evaluation.csv", index=False)
    print("Kalman evaluation saved.")
    return table


# ------------------------------------------------------------ charts

def charts(summary, convergence, exact, kalman):
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    colors = {"Random Selection": "#BAB0AC", "Greedy": "#4C78A8",
              "Hill Climbing": "#F58518", "Simulated Annealing": "#54A24B"}

    # 1. Coverage vs budget.
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), sharey=True)
    for ax, project in zip(axes, PROJECTS):
        part = summary[summary["project"] == project]
        for name in METHODS:
            m = part[part["optimizer"] == name]
            ax.errorbar(m["budget_fraction"] * 100, m["mean_coverage"],
                        yerr=m["std_coverage"], marker="o", label=name,
                        color=colors[name], capsize=3)
        ax.set_xscale("log")
        ax.set_xticks([1, 2, 5, 10, 30, 70])
        ax.set_xticklabels(["1", "2", "5", "10", "30", "70"])
        ax.set_title(project)
        ax.set_xlabel("Time budget (% of full suite, log scale)")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("Coverage kept (%)")
    axes[0].legend()
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "coverage_vs_budget.png", dpi=200)
    plt.close(fig)

    # 1b. Bug detection vs budget.
    if summary["mean_mutants_caught"].notna().any():
        fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), sharey=True)
        for ax, project in zip(axes, PROJECTS):
            part = summary[summary["project"] == project]
            for name in METHODS:
                m = part[part["optimizer"] == name]
                ax.errorbar(m["budget_fraction"] * 100, m["mean_mutants_caught"],
                            yerr=m["std_mutants_caught"], marker="o", label=name,
                            color=colors[name], capsize=3)
            ax.set_xscale("log")
            ax.set_xticks([1, 2, 5, 10, 30, 70])
            ax.set_xticklabels(["1", "2", "5", "10", "30", "70"])
            ax.set_title(project)
            ax.set_xlabel("Time budget (% of full suite, log scale)")
            ax.grid(alpha=0.3)
        axes[0].set_ylabel("Seeded bugs still caught (%)")
        axes[0].legend()
        fig.tight_layout()
        fig.savefig(CHARTS_DIR / "fault_detection_vs_budget.png", dpi=200)
        plt.close(fig)

    # 2. Convergence at a 5% budget.
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    for ax, project in zip(axes, PROJECTS):
        part = convergence[convergence["project"] == project]
        for name in ["Hill Climbing", "Simulated Annealing"]:
            m = part[part["optimizer"] == name]
            ax.plot(m["iteration"], m["best_coverage"], label=name, color=colors[name])
        ax.set_title(f"{project}, 5% budget")
        ax.set_xlabel("Iteration (SA) / step (HC)")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("Best coverage so far (%)")
    axes[0].legend()
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "convergence.png", dpi=200)
    plt.close(fig)

    # 3. Search effort on small instances.
    effort = exact.groupby("project")[[
        "fullcover_UCS_nodes_expanded", "fullcover_AStar_nodes_expanded",
        "CSP_plain_backtracks", "CSP_MRV_FC_backtracks"]].mean()
    effort.columns = ["UCS", "A*", "Plain backtracking", "MRV + forward checking"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    effort[["UCS", "A*"]].plot.bar(ax=axes[0], rot=0)
    axes[0].set_title("Nodes expanded, cheapest full coverage (mean of 10)")
    effort[["Plain backtracking", "MRV + forward checking"]].plot.bar(ax=axes[1], rot=0)
    axes[1].set_title("CSP backtracks (mean of 10 instances)")
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "search_effort.png", dpi=200)
    plt.close(fig)

    # 4. Gap to optimum.
    labels = ["UCS", "AStar", "CSP_MRV_FC", "Greedy", "Hill_Climbing",
              "Simulated_Annealing", "Random_Selection"]
    gaps = [exact[f"{l}_gap_pct"].mean() for l in labels]
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.bar([l.replace("_", " ") for l in labels], gaps, color="#4C78A8")
    ax.set_ylabel("Mean gap to optimum (%)")
    ax.set_title("Gap to the true optimum, 30 small sub-suites")
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "gap_to_optimum.png", dpi=200)
    plt.close(fig)

    # 5. Kalman vs raw timings.
    pivot = kalman.pivot(index="project", columns="estimate", values="mae_ms")
    fig, ax = plt.subplots(figsize=(9, 4.5))
    pivot[["Single run", "Mean of 5 runs", "Kalman filter"]].plot.bar(ax=ax, rot=0)
    ax.set_ylabel("MAE vs held-out runs (ms)")
    ax.set_title("Duration estimate error (estimates from runs 1-5, checked on runs 6-10)")
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "kalman_vs_raw.png", dpi=200)
    plt.close(fig)
    print("Charts saved to", CHARTS_DIR)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=30)
    args = parser.parse_args()

    RESULTS_DIR.mkdir(exist_ok=True)
    suites = {project: load_project(key) for project, key in PROJECTS.items()}

    kill_data = {project: load_kill_matrix(key) for project, key in PROJECTS.items()}
    for project, (_, detectable) in kill_data.items():
        print(f"{project}: {len(detectable)} detectable mutants")

    main_benchmark(suites, kill_data)
    summary, convergence = budget_sweep(suites, args.seeds, kill_data)
    exact = exact_small_instances(suites)
    kalman = kalman_evaluation(suites)
    charts(summary, convergence, exact, kalman)
    create_comparison_charts()


if __name__ == "__main__":
    main()

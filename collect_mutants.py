"""
Seed small bugs (mutants) into a project and record which tests catch them.

    python collect_mutants.py --project data/raw/tinydb --name tinydb
    python collect_mutants.py --project data/raw/boltons --name boltons --mutants 150

Needs the project cloned in data/raw/ (same commit as the coverage data)
and its test dependencies installed. Reads
data/processed/<name>_coverage_matrix.csv and writes:
    data/processed/<name>_mutants.csv       one row per mutant
    data/processed/<name>_kill_matrix.csv   one row per (mutant, test that catches it)
"""

import argparse
import csv
import time
from pathlib import Path

from src.collect.mutation import generate_mutants, load_coverage, run_mutants

DATA_DIR = Path("data/processed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--mutants", type=int, default=150)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--timeout", type=int, default=60, help="Seconds per mutant run")
    args = parser.parse_args()

    covered_by_file, tests_by_line = load_coverage(
        DATA_DIR / f"{args.name}_coverage_matrix.csv"
    )

    mutants, pool_size = generate_mutants(
        args.project, covered_by_file, max_mutants=args.mutants, seed=args.seed
    )
    print(f"{args.name}: {pool_size} possible mutants on covered lines, sampled {len(mutants)}")

    start = time.perf_counter()
    kills, passing = run_mutants(args.project, mutants, tests_by_line, timeout=args.timeout)
    print(f"Finished in {time.perf_counter() - start:.0f} s")

    with (DATA_DIR / f"{args.name}_mutants.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=[
            "mutant_id", "file", "line", "operator", "original", "replacement",
            "tests_run", "tests_killing", "detected",
        ])
        writer.writeheader()
        for m in mutants:
            run = [t for t in tests_by_line.get((m["file"], m["line"]), []) if t in set(passing)]
            killed = kills.get(m["mutant_id"], set())
            writer.writerow({
                "mutant_id": m["mutant_id"], "file": m["file"], "line": m["line"],
                "operator": m["operator"], "original": m["original"],
                "replacement": m["replacement"], "tests_run": len(run),
                "tests_killing": len(killed), "detected": bool(killed),
            })

    with (DATA_DIR / f"{args.name}_kill_matrix.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["mutant_id", "test_node_id"])
        for mutant_id, killed in sorted(kills.items()):
            for test in sorted(killed):
                writer.writerow([mutant_id, test])

    detected = sum(1 for k in kills.values() if k)
    print(f"Detected by the full suite: {detected} of {len(mutants)} mutants")
    print("Saved:", DATA_DIR / f"{args.name}_mutants.csv", "and", DATA_DIR / f"{args.name}_kill_matrix.csv")


if __name__ == "__main__":
    main()

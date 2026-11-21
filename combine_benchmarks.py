import csv
from pathlib import Path

files = {
    "TinyDB": Path("results/tinydb_benchmark.csv"),
    "Toolz": Path("results/toolz_benchmark.csv"),
    "Boltons": Path("results/boltons_benchmark.csv")
}

budgets = {
    "TinyDB": 0.24,
    "Toolz": 0.452752,
    "Boltons": 1.8701
}

output = Path("results/combined_benchmark.csv")

combined = []

for project, path in files.items():
    with path.open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):

            optimizer = row["optimizer"]

            if optimizer == "Random":
                optimizer = "Random Selection"

            combined.append({
                "project": project,
                "optimizer": optimizer,
                "selected_tests": row.get("selected_tests", ""),
                "selected_execution_time": (
                    row.get("selected_execution_time")
                    or row.get("test_time_seconds", "")
                ),
                "coverage_percentage": row["coverage_percentage"],
                "feasible": row["feasible"],
                "optimizer_runtime_seconds": row["optimizer_runtime_seconds"],
                "budget_seconds": (
                    row.get("budget_seconds")
                    or budgets[project]
                )
            })

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

with output.open("w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=fields)
    writer.writeheader()
    writer.writerows(combined)

print("Combined benchmark created.")
print("Total benchmark records:", len(combined))
print("Projects:", len(files))
print("Saved to:", output)

for project in files:
    count = sum(row["project"] == project for row in combined)
    print(f"{project}: {count} optimizer results")

import csv
from pathlib import Path
from src.collect.test_discovery import discover_test_cases
from src.collect.timing_collector import collect_repeated_timings

project = Path("data/raw/boltons").resolve()
tests = discover_test_cases(project)
output = Path("data/processed/boltons_timing_runs.csv")
temp = Path("data/processed")

fields = ["project", "run_number", "node_id", "status", "duration_seconds"]

with output.open("w", newline="", encoding="utf-8") as final_file:
    writer = csv.DictWriter(final_file, fieldnames=fields)
    writer.writeheader()

    for start in range(0, len(tests), 40):
        batch = tests[start:start + 40]
        batch_file = temp / f"boltons_batch_{start}.csv"

        print(f"\nBatch {start // 40 + 1}: tests {start + 1}-{start + len(batch)}")

        collect_repeated_timings(
            project, batch, repetitions=10, output_path=batch_file
        )

        with batch_file.open(newline="", encoding="utf-8") as source:
            writer.writerows(csv.DictReader(source))

        batch_file.unlink()

print("\nALL TIMING BATCHES COMPLETED")
print("Saved:", output)

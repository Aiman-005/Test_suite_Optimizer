import csv
from pathlib import Path
from src.collect.test_discovery import discover_test_cases
from src.collect.coverage_collector import collect_test_coverage

project_path = Path("data/raw/boltons").resolve()
output_path = Path("data/processed/boltons_coverage_matrix.csv")

test_cases = discover_test_cases(project_path)
batch_size = 40
all_rows = []
tests_with_coverage = set()

for start in range(0, len(test_cases), batch_size):
    batch = test_cases[start:start + batch_size]
    batch_number = start // batch_size + 1

    print(f"Processing batch {batch_number}: {len(batch)} tests...")

    result = collect_test_coverage(project_path, batch)

    if result["pytest_exit_code"] != 0:
        raise RuntimeError(f"Coverage failed in batch {batch_number}")

    for node_id, files in result["coverage"].items():
        if files:
            tests_with_coverage.add(node_id)

        for source_file, lines in files.items():
            all_rows.append({
                "test_node_id": node_id,
                "source_file": source_file,
                "covered_lines": ";".join(map(str, lines))
            })

    print(f"  Tests with coverage: {result['tests_with_coverage']}")

with output_path.open("w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(
        file,
        fieldnames=["test_node_id", "source_file", "covered_lines"]
    )
    writer.writeheader()
    writer.writerows(all_rows)

print("\nCoverage collection complete.")
print("Discovered tests:", len(test_cases))
print("Tests with coverage:", len(tests_with_coverage))
print("Coverage rows:", len(all_rows))
print("Saved to:", output_path)

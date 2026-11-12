
import csv
from pathlib import Path


def build_comparison_report(results):
    """Convert optimizer results into a structured comparison report."""

    report = []

    for algorithm, result in results.items():
        report.append({
            "algorithm": algorithm,
            "selected_tests": result["selected_tests"],
            "number_of_tests": len(result["selected_tests"]),
            "total_time": result["total_time"],
            "coverage_percentage": result["coverage_percentage"],
            "feasible": result["feasible"]
        })

    return report


def format_comparison_report(report):
    """Format comparison results as a readable table."""

    headers = [
        "Algorithm",
        "Selected Tests",
        "Count",
        "Time",
        "Coverage",
        "Feasible"
    ]

    rows = []

    for result in report:
        rows.append([
            result["algorithm"],
            ", ".join(result["selected_tests"]) or "None",
            str(result["number_of_tests"]),
            f'{result["total_time"]:.2f}',
            f'{result["coverage_percentage"]:.2f}%',
            "Yes" if result["feasible"] else "No"
        ])

    widths = [
        max(len(headers[i]), *(len(row[i]) for row in rows))
        for i in range(len(headers))
    ]

    header_line = " | ".join(
        headers[i].ljust(widths[i])
        for i in range(len(headers))
    )

    separator = "-+-".join("-" * width for width in widths)

    table_rows = [
        " | ".join(
            row[i].ljust(widths[i])
            for i in range(len(headers))
        )
        for row in rows
    ]

    return "\n".join([header_line, separator] + table_rows)


def export_comparison_csv(report, output_path):
    """Export comparison results to a CSV file."""

    fieldnames = [
        "algorithm",
        "selected_tests",
        "number_of_tests",
        "total_time",
        "coverage_percentage",
        "feasible"
    ]

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        writer.writeheader()

        for result in report:
            row = result.copy()
            row["selected_tests"] = ", ".join(row["selected_tests"])
            writer.writerow(row)

    return output_path

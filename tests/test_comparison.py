
from pathlib import Path
from src.evaluation.comparison import export_comparison_csv
from src.core.data_loader import load_problem
from src.app.experiment_runner import run_all_optimizers
from src.evaluation.comparison import (
    build_comparison_report,
    format_comparison_report
)


def get_comparison_report():

    project_root = Path(__file__).resolve().parents[1]

    dataset_path = (
        project_root / "data" / "processed" / "sample_project.json"
    )

    problem = load_problem(dataset_path)

    results = run_all_optimizers(problem)

    return build_comparison_report(results)


def test_comparison_contains_all_algorithms():

    report = get_comparison_report()

    algorithms = {
        row["algorithm"] for row in report
    }

    assert algorithms == {
        "Random Selection",
        "Greedy",
        "Hill Climbing",
        "Simulated Annealing",
        "UCS",
        "A*",
        "CSP"
    }


def test_comparison_contains_required_metrics():

    report = get_comparison_report()

    for row in report:

        assert "selected_tests" in row
        assert "number_of_tests" in row
        assert "total_time" in row
        assert "coverage_percentage" in row
        assert "feasible" in row


def test_comparison_results_respect_budget():

    report = get_comparison_report()

    for row in report:

        assert row["feasible"] is True
        assert row["total_time"] <= 8


def test_comparison_table_is_readable():

    report = get_comparison_report()

    table = format_comparison_report(report)

    assert "Algorithm" in table
    assert "Selected Tests" in table
    assert "Coverage" in table
    assert "Random Selection" in table
    assert "CSP" in table

def test_comparison_csv_export(tmp_path):

    report = get_comparison_report()

    output_file = tmp_path / "reports" / "comparison.csv"

    exported_file = export_comparison_csv(
        report,
        output_file
    )

    assert exported_file.exists()

    import csv

    with exported_file.open(
        "r",
        newline="",
        encoding="utf-8"
    ) as file:

        rows = list(csv.DictReader(file))

    assert len(rows) == 7
    assert rows[0]["algorithm"] == "Random Selection"
    assert "coverage_percentage" in rows[0]
import pandas as pd
import pytest

from frontend.components.mutation_results import add_mutant_count_columns


def test_add_mutant_counts_includes_mutants_undetected_by_full_suite():
    sweep = pd.DataFrame({
        "mutants_caught_percentage": [50.0, 25.0],
    })

    result = add_mutant_count_columns(
        sweep,
        total_mutants=6,
        detectable_mutants=4,
    )

    assert result["mutants_caught_count"].tolist() == [2.0, 1.0]
    assert result["mutants_survived_count"].tolist() == [4.0, 5.0]
    assert result["mutant_detection_percentage"].tolist() == pytest.approx(
        [100 / 3, 100 / 6]
    )


def test_add_mutant_counts_rejects_scores_inconsistent_with_kill_matrix():
    sweep = pd.DataFrame({"mutants_caught_percentage": [33.0]})

    with pytest.raises(ValueError, match="integer kill-matrix counts"):
        add_mutant_count_columns(
            sweep,
            total_mutants=6,
            detectable_mutants=4,
        )


def test_add_mutant_counts_rejects_non_numeric_scores():
    sweep = pd.DataFrame({"mutants_caught_percentage": ["invalid"]})

    with pytest.raises(ValueError):
        add_mutant_count_columns(
            sweep,
            total_mutants=6,
            detectable_mutants=4,
        )

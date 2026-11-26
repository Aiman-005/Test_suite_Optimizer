import pandas as pd
import pytest

from src.ai_demos.markov_model import run_markov_experiment


def timing_observations(sequence, tests=3):
    rows = []
    for test_number in range(tests):
        for run_number, duration in enumerate(sequence, start=1):
            rows.append({
                "node_id": f"test_{test_number}",
                "run_number": run_number,
                "status": "passed",
                "duration_seconds": duration,
            })
    return pd.DataFrame(rows)


def test_learns_transitions_and_scores_held_out_observations():
    timing = timing_observations([1, 5, 9, 1, 5, 9, 1, 5, 9, 1])

    result = run_markov_experiment(timing)

    assert result.training_observations == 24
    assert result.training_transitions == 21
    assert result.held_out_predictions == 3
    assert result.transition_counts.loc["Fast", "Medium"] == 9
    assert result.transition_counts.loc["Medium", "Slow"] == 6
    assert result.transition_counts.loc["Slow", "Fast"] == 6
    assert result.transition_probabilities.loc["Fast", "Medium"] == 1
    assert result.accuracy == 1
    assert result.baseline_accuracy == 0


def test_excludes_skipped_tests_and_does_not_bridge_missing_runs():
    timing = timing_observations([1, 5, 9, 1, 5, 9, 1, 5, 9, 1])
    timing.loc[
        (timing["node_id"] == "test_0") & (timing["run_number"] == 3),
        "status",
    ] = "skipped"

    result = run_markov_experiment(timing)

    assert result.training_transitions == 19
    assert result.held_out_predictions == 3
    assert result.transition_counts.loc["Medium", "Fast"] == 0


def test_rejects_missing_timing_columns():
    with pytest.raises(ValueError, match="missing required columns"):
        run_markov_experiment(pd.DataFrame({"node_id": ["test"]}))

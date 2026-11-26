"""Markov-model experiment for repeated test execution timings.

The first eight runs per test train the state boundaries and transition
probabilities. The transition from run 9 to run 10 is held out for evaluation.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path("data/processed")
PROJECTS = ("tinydb", "toolz", "boltons")
STATES = ("Fast", "Medium", "Slow")
TRAIN_RUNS = range(1, 9)
VALIDATION_RUNS = (9, 10)


@dataclass(frozen=True)
class MarkovResult:
    transition_counts: pd.DataFrame
    transition_probabilities: pd.DataFrame
    predictions: pd.DataFrame
    confusion_matrix: pd.DataFrame
    state_counts: pd.Series
    medium_upper_seconds: float
    slow_lower_seconds: float
    training_observations: int
    training_transitions: int
    held_out_predictions: int
    accuracy: float
    baseline_accuracy: float
    fallback_predictions: int


def _state_for_duration(
    duration: float, medium_upper_seconds: float, slow_lower_seconds: float
) -> str:
    if duration <= medium_upper_seconds:
        return "Fast"
    if duration <= slow_lower_seconds:
        return "Medium"
    return "Slow"


def run_markov_experiment(timing: pd.DataFrame) -> MarkovResult:
    """Train on runs 1-8 and evaluate each test's run-9-to-10 transition."""
    required_columns = {
        "node_id", "run_number", "status", "duration_seconds"
    }
    missing_columns = required_columns.difference(timing.columns)
    if missing_columns:
        raise ValueError(
            "Timing data is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    observations = timing.loc[timing["status"] == "passed"].copy()
    observations["run_number"] = pd.to_numeric(
        observations["run_number"], errors="raise"
    )
    observations["duration_seconds"] = pd.to_numeric(
        observations["duration_seconds"], errors="raise"
    )
    observations = observations[
        observations["duration_seconds"].gt(0)
        & np.isfinite(observations["duration_seconds"])
    ]

    if observations["node_id"].isna().any():
        raise ValueError("Passed timing observations must have a test node_id.")
    if observations.duplicated(["node_id", "run_number"]).any():
        raise ValueError("Each test must have at most one observation per run.")

    training = observations[
        observations["run_number"].isin(TRAIN_RUNS)
    ].copy()
    if len(training) < 3:
        raise ValueError("At least three training timing observations are required.")

    medium_upper, slow_lower = np.quantile(
        training["duration_seconds"], [1 / 3, 2 / 3]
    )

    observations["state"] = observations["duration_seconds"].map(
        lambda value: _state_for_duration(
            value, medium_upper, slow_lower
        )
    )
    training = observations[
        observations["run_number"].isin(TRAIN_RUNS)
    ]

    counts = pd.DataFrame(0, index=STATES, columns=STATES, dtype=int)
    transition_total = 0
    for _, sequence in training.groupby("node_id", sort=False):
        sequence = sequence.sort_values("run_number")
        runs = sequence["run_number"].to_numpy()
        states = sequence["state"].to_numpy()
        for previous_run, next_run, previous, following in zip(
            runs[:-1], runs[1:], states[:-1], states[1:]
        ):
            if next_run == previous_run + 1:
                counts.loc[previous, following] += 1
                transition_total += 1

    if transition_total == 0:
        raise ValueError("Training data contains no consecutive timing observations.")

    row_totals = counts.sum(axis=1)
    probabilities = counts.div(row_totals.replace(0, np.nan), axis=0).fillna(0.0)
    probabilities.index.name = "From state"
    probabilities.columns.name = "To state"

    next_state_counts = counts.sum(axis=0)
    baseline_state = max(STATES, key=lambda state: next_state_counts[state])

    predictions = []
    validation = observations[
        observations["run_number"].isin(VALIDATION_RUNS)
    ]
    for node_id, sequence in validation.groupby("node_id", sort=False):
        by_run = sequence.set_index("run_number")
        if not all(run in by_run.index for run in VALIDATION_RUNS):
            continue

        previous_state = by_run.loc[9, "state"]
        actual_state = by_run.loc[10, "state"]
        probabilities_from_state = probabilities.loc[previous_state]
        if probabilities_from_state.sum() == 0:
            predicted_state = baseline_state
            fallback = True
        else:
            predicted_state = max(
                STATES, key=lambda state: probabilities_from_state[state]
            )
            fallback = False

        predictions.append({
            "node_id": node_id,
            "from_run": VALIDATION_RUNS[0],
            "to_run": VALIDATION_RUNS[1],
            "previous_state": previous_state,
            "predicted_state": predicted_state,
            "actual_state": actual_state,
            "correct": predicted_state == actual_state,
            "baseline_correct": baseline_state == actual_state,
            "used_fallback": fallback,
        })

    if not predictions:
        raise ValueError(
            "No tests have passing observations for both validation runs 9 and 10."
        )

    prediction_frame = pd.DataFrame(predictions)
    confusion = pd.DataFrame(0, index=STATES, columns=STATES, dtype=int)
    for row in prediction_frame.itertuples(index=False):
        confusion.loc[row.actual_state, row.predicted_state] += 1
    confusion.index.name = "Actual state"
    confusion.columns.name = "Predicted state"

    state_counts = (
        training["state"]
        .value_counts()
        .reindex(STATES, fill_value=0)
        .rename("observations")
    )

    return MarkovResult(
        transition_counts=counts,
        transition_probabilities=probabilities,
        predictions=prediction_frame,
        confusion_matrix=confusion,
        state_counts=state_counts,
        medium_upper_seconds=float(medium_upper),
        slow_lower_seconds=float(slow_lower),
        training_observations=len(training),
        training_transitions=transition_total,
        held_out_predictions=len(prediction_frame),
        accuracy=float(prediction_frame["correct"].mean()),
        baseline_accuracy=float(prediction_frame["baseline_correct"].mean()),
        fallback_predictions=int(prediction_frame["used_fallback"].sum()),
    )


def main() -> None:
    for project in PROJECTS:
        timing = pd.read_csv(DATA_DIR / f"{project}_timing_runs.csv")
        result = run_markov_experiment(timing)
        print(
            f"\n{project.upper()}: {result.training_transitions} training "
            f"transitions, {result.held_out_predictions} held-out predictions, "
            f"accuracy={result.accuracy:.1%}, "
            f"majority baseline={result.baseline_accuracy:.1%}"
        )
        print(result.transition_probabilities.round(3).to_string())


if __name__ == "__main__":
    main()

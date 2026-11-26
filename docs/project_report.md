# Project Report: Markov Model Experiment

## Purpose

This supporting AI experiment models how a test's execution-time category
changes between repeated runs. It is independent of, and does not change, the
test-selection optimization algorithms or their configurations.

## Data and method

The experiment uses the collected `data/processed/*_timing_runs.csv` data for
TinyDB, toolz and boltons. Only observations marked `passed` with positive,
finite durations are used. Each test's observations are ordered by recorded
run number; a transition is counted only between consecutive run numbers.

For each project, the first eight runs train a first-order Markov model:

1. The one-third and two-thirds quantiles of training durations define the
   Fast, Medium and Slow categories. Boundaries are learned from training data
   only.
2. Consecutive states from runs 1–8 form the training transition counts.
   Dividing each row by its total gives the transition probability matrix.
3. For each test with passing observations in both runs 9 and 10, the
   run-9 state is used to predict run 10. The most probable next state is the
   prediction. The comparison baseline predicts the most common next state in
   the training transitions.

Skipped and zero-duration records do not contribute. The experiment evaluates
each eligible test's single run-9-to-10 transition; it does not reuse those
held-out observations to train state boundaries or transition probabilities.

## Results

The metrics below were calculated from the checked-in timing CSVs.

| Project | Passing tests with complete runs | Training transitions | Held-out predictions | Markov accuracy | Majority-state baseline |
|---|---:|---:|---:|---:|---:|
| TinyDB | 228 | 1,596 | 228 | 64.9% | 31.6% |
| toolz | 193 | 1,351 | 193 | 77.7% | 53.4% |
| boltons | 620 | 4,340 | 620 | 74.2% | 33.4% |

These observations are sufficient to display and evaluate an empirical
three-state transition matrix for each collected project. In this split, the
model outperforms the simple majority-state baseline for all three projects.
The dashboard reports the project-specific probability matrix, held-out
accuracy, baseline, confusion counts, and example predictions.

## Limitations

- There are only ten repeated observations per test. The final one-step
  run-9-to-10 prediction is the only held-out transition for each test.
- Tests come from the same collected suites and machine/environment; the
  evaluation does not establish generalization to different projects,
  versions, or execution environments.
- Timing states use project-specific quantile cutoffs, so the state labels
  are relative to each project's training timing distribution, not shared
  absolute duration thresholds.
- Consecutive test runs may share environmental effects; individual
  transitions should not be treated as fully independent samples.
- This is a descriptive supporting experiment, not an optimizer input or a
  replacement for the existing Kalman duration estimator.

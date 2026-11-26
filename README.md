# Test Suite Optimizer

**Running fewer tests without missing bugs.**
AL-2002 Artificial Intelligence Lab · FAST-NUCES Karachi · Fall 2026

Large projects re-run hundreds of automated tests after every change, and many of those tests check the same lines of code. This project chooses a smaller set of tests that still covers as much code as possible within a time budget (for example, "run only 5% of the usual test time"). Choosing that set is an NP-hard budgeted maximum-coverage problem, so it is solved with AI search: hill climbing and simulated annealing on full suites, compared with greedy and random baselines, and checked against the true optimum found by uniform-cost search, A\* and a CSP solver on small sub-suites. Test durations come from a Kalman filter over 10 noisy timing runs, and every selection is checked by seeding small bugs (mutants) into the code and counting how many the smaller test set still catches. Supporting AI studies (K-Means clustering, linear regression and a Markov model of repeated execution-time states) analyse the collected data separately from the optimizers. All data comes from the real test suites of three open-source Python projects.

---

## Author

| Name | Roll number | Contribution |
|---|---|---|
| Aiman Farooqui | 24k-3077 | Solo project: data collection, Kalman filter, all optimisers and solvers, ML studies, experiments and dashboard |

---

## AI techniques used

| Lab | Technique | Where in the code |
|---|---|---|
| 01–02 | Python and OOP | Abstract `Optimizer` base class (`src/algorithms/base.py`) that every optimiser inherits and overrides `optimize()`; abstract `SearchSolver` with `UniformCostSearch` and `AStarSearch` overriding `priority()` |
| 03 | Agents and PEAS | Utility-based agent; PEAS in `docs/proposal.pdf` and the report |
| 04 | Uniform-cost search | `src/algorithms/search_optimization.py`: `UniformCostSearch` (cheapest full coverage), `SearchOptimizer.uniform_cost_search` (best coverage within budget) |
| 05 | A\* search | same file: `AStarSearch`, with an admissible heuristic (max of a rate bound and an essential-test bound) |
| 06 | Hill climbing (random restarts), simulated annealing | `src/algorithms/hill_climbing.py`, `simulated_annealing.py`, `selection_state.py` |
| 07 | CSP: backtracking, MRV, forward checking | `src/algorithms/csp_optimizer.py` (plain and MRV + FC variants, backtrack counts) |
| 09 | Kalman filter | `src/core/kalman_filter.py`, `build_kalman_estimates.py` |
| 10 | Exploratory data analysis | `notebooks/eda.ipynb`: duration distribution, timing noise, coverage overlap, lines covered by one test |
| ML | Unsupervised learning: K-Means | `src/ai_demos/kmeans_clustering.py` |
| ML | Supervised learning: linear regression | `src/ai_demos/linear_regression.py` (5-fold cross-validation, compared with two baselines) |
| ML | Markov model of execution-time states | `src/ai_demos/markov_model.py` (transition probabilities learned from runs 1–8; held-out prediction on runs 9–10) |

---

## Project structure

```
Test_suite_Optimizer/
├── README.md
├── requirements.txt
├── collect_project.py          # collect coverage + 10 timing runs for one project
├── build_kalman_estimates.py   # timing runs -> Kalman duration estimates
├── collect_mutants.py          # seed bugs (mutants) and record which tests catch them
├── run_experiments.py          # reproduces every optimiser result and chart
├── docs/proposal.pdf
├── notebooks/eda.ipynb        # exploratory data analysis (Lab 10)
├── data/
│   ├── raw/                    # cloned projects (not committed)
│   └── processed/              # committed CSVs: everything the code needs
├── src/
│   ├── core/                   # TestSuite, SelectionProblem, KalmanDurationEstimator, data loader
│   ├── algorithms/             # Optimizer base class, random, greedy, hill climbing, simulated annealing, UCS/A*, CSP
│   ├── collect/                # test discovery, coverage, timing and mutation (bug seeding)
│   ├── app/                    # project analyser and experiment runner used by the dashboard
│   ├── evaluation/             # comparison tables and charts
│   └── ai_demos/               # K-Means, linear regression and Markov model
├── frontend/                   # Streamlit dashboard (app.py + pages/)
├── results/                    # CSV results, charts/ and ml/
└── tests/                      # 59 unit tests (pytest)
```

---

## Setup (Windows)

Requires Python 3.10 or newer. No internet connection or API key is needed after installation.

```powershell
git clone https://github.com/Aiman-005/Test_suite_Optimizer.git
cd Test_suite_Optimizer
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

On macOS / Linux use `source .venv/bin/activate`. The processed data is already in `data/processed/`, so nothing needs to be collected.

---

## How to run

```powershell
python -m pytest tests                        # 59 unit tests
python run_experiments.py                     # all optimiser experiments + charts (10-20 min; --seeds 5 is quicker)
python -m src.ai_demos.kmeans_clustering      # K-Means results in results/ml/
python -m src.ai_demos.linear_regression      # regression results in results/ml/
python -m src.ai_demos.markov_model           # Markov matrices and held-out predictions
streamlit run frontend/app.py                 # dashboard at http://localhost:8501
jupyter notebook notebooks/eda.ipynb          # exploratory data analysis
```

**Collect data for a project yourself (optional).** Clone the project into `data/raw/`, install its test dependencies in the same environment, then:

```powershell
python collect_project.py --project data/raw/tinydb --name tinydb
```

This writes the coverage matrix, the 10 timing runs, the Kalman estimates and the commit hash to `data/processed/`. To seed bugs and build the kill matrix (about 2 minutes per project):

```powershell
python collect_mutants.py --project data/raw/tinydb --name tinydb
```

---

## Data source

Only derived data (coverage and timings) is stored here, not the projects' source code.

| Project | Link | Licence | Commit used | Tests | Coverable lines | Seeded bugs (caught by full suite) |
|---|---|---|---|---|---|---|
| TinyDB | https://github.com/msiemens/tinydb | MIT | `edff96aeb2616402e9489d46e90a592c05565621` | 228 | 499 | 124 (116) |
| toolz | https://github.com/pytoolz/toolz | BSD-3-Clause | `451af60dec590a6010e2babdbf391ea8f815122f` | 193 | 1,036 | 150 (123) |
| boltons | https://github.com/mahmoud/boltons | BSD-3-Clause | `d31d821d56c8f7756af9c30a864077f2e5855321` | 620 | 4,368 | 150 (118) |

---

## Results

All numbers come from `python run_experiments.py` (30 seeds) and the two ML scripts; charts are in `results/charts/`.

**Coverage kept at tight budgets** (mean of 30 seeds; greedy is deterministic):

| Project | Budget | Random | Greedy | Hill climbing | Simulated annealing |
|---|---|---|---|---|---|
| TinyDB | 2% | 50.6% | 93.8% | 94.4% | **94.8%** |
| toolz | 5% | 55.5% | 90.6% | **94.7%** | 90.6% |
| boltons | 1% | 27.8% | 83.7% | **83.7%** | 83.7% |

Hill climbing and simulated annealing start from the greedy solution, so they are never worse than greedy; at 10% of the suite time or more, every guided method keeps 98–100% coverage.

**Seeded bugs still caught** (% of the bugs the full suite catches; mean of 30 seeds, 5% budget):

| Project | Random | Greedy | Hill climbing | Simulated annealing |
|---|---|---|---|---|
| TinyDB | 47.5% | 92.2% | 91.6% | 92.2% |
| toolz | 55.4% | 95.1% | 91.2% | 95.1% |
| boltons | 45.0% | 94.1% | 94.1% | 94.1% |

Even at 100% line coverage, the guided methods catch at most 93.1% (TinyDB), 97.6% (toolz) and 97.5% (boltons) of the bugs: running a line is not the same as checking its result. Higher coverage does not always mean more bugs caught; on toolz at 5%, hill climbing covers more lines than greedy (94.7% vs 90.6%) but catches fewer bugs (91.2% vs 95.1%). Chart: `results/charts/fault_detection_vs_budget.png`.

**Small sub-suites (30 instances of 15 tests, 30% budget), compared with the brute-force optimum:**

| Method | Optimal on | Mean gap | Worst gap |
|---|---|---|---|
| UCS, A\*, CSP (both variants) | 30 / 30 | 0.00% | 0.00% |
| Hill climbing | 29 / 30 | 0.01% | 0.40% |
| Simulated annealing | 27 / 30 | 0.35% | 8.99% |
| Greedy | 22 / 30 | 0.74% | 8.99% |
| Random | 10 / 30 | 12.70% | 66.67% |

**Search effort:** for the cheapest full-coverage selection, A\* expands 52% fewer nodes than UCS on TinyDB (118 vs 247), 20% fewer on boltons and 10% fewer on toolz, with the same optimal cost. MRV + forward checking cuts CSP backtracks from 1,186–3,156 to about 1 per instance.

**Kalman filter:** predicting a selection's total time from runs 1–5, the error against runs 6–10 is 8.5% with Kalman vs 65.2% with a single run on toolz, and 10.0% vs 11.2% on TinyDB; on boltons the plain mean is slightly better (5.9% vs 6.6%).

**Supervised learning (linear regression, 5-fold CV):** R² = 0.916 (TinyDB), 0.999 (toolz), 0.979 (boltons). It beats the historical-mean baseline on R² for TinyDB and toolz, but not on boltons, so past timings already carry most of the signal.

**Unsupervised learning (K-Means on log-scaled features):** k = 3, 2 and 3 with silhouette 0.59, 0.55 and 0.43; TinyDB and boltons each have a cluster of slow, low-yield tests (33 and 19 covered lines per millisecond, against 110–450 for their other clusters); toolz splits into small fast tests and larger, slower ones of similar yield.

**Markov model (Fast/Medium/Slow timing states):** state cutoffs are the one-third and two-thirds quantiles of passing observations from runs 1–8, computed separately for each project. Consecutive per-test transitions in those runs train the transition matrix; each passing test with runs 9 and 10 supplies one held-out next-state prediction. The Markov model achieved 64.9% accuracy on TinyDB (31.6% majority-state baseline), 77.7% on toolz (53.4% baseline), and 74.2% on boltons (33.4% baseline). The training split contained 1,596, 1,351 and 4,340 transitions respectively, evaluated on 228, 193 and 620 held-out transitions. This is a useful small one-step experiment, not evidence of generalization to other projects or environments: all predictions come from one final run pair on the same suites, and only ten timing runs per test were collected. See [the project report](docs/project_report.md) for the protocol and detailed results.

---

## Known limitations

- **Simple mutants:** seeded bugs are single operator or constant changes on covered lines (124–150 per project), so bug-detection numbers estimate real fault detection rather than measure it.
- **Line coverage only:** branch and data-flow coverage are not used.
- **Pre-collected data:** selection does not look at which lines the latest commit changed.
- **Exact search on small instances only:** UCS, A\* and the CSP run on 15-test sub-suites, because they are exponential.
- **Fast suites:** all three suites take under 4 s in total, so absolute savings are small, although the method is the same for slow suites.
- **Markov timing experiment:** only ten repeated runs are available per test; evaluation uses the final run pair from the same collected suites, so it does not measure transfer to future environments or independent projects.
- **No flaky-test handling. Python projects only.**

---

## Future work

- Richer mutants (statement deletion, return-value changes) and more projects with slow suites.
- Change-aware selection based on the lines changed in the latest commit.
- Package as a pytest plugin (`pytest --optimize --budget=5m`), publish on PyPI and offer a GitHub Action.

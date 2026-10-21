# Test Suite Optimizer

**Running fewer tests without missing bugs.**
AL-2002 Artificial Intelligence Lab · FAST-NUCES Karachi · Fall 2026

Large software projects re-run hundreds of automated tests after every code change, and many of those tests check the same lines of code. This project uses AI search to choose a smaller set of tests that still covers as much of the code as possible within a time budget, for example "run only 30% of the usual test time". Choosing that set is an NP-hard combinatorial problem (a suite of 300 tests has 2^300 possible subsets), so the project solves it with local search (hill climbing and simulated annealing), compares the results against a greedy baseline, and measures how close they get to the true optimum found by exact search (UCS, A* and a CSP) on smaller instances. Test durations are estimated with a Kalman filter because single timings are noisy, and every selection is checked by inserting small bugs into the code and measuring how many of them the smaller test set still catches. The data comes from the real test suites of three open-source Python projects.

---

## Author

| Name | Roll number | What I built |
|---|---|---|
| Aiman Farooqu | 24k-3077 | Solo project: everything, including data collection, the Kalman filter, all optimizers, exact solvers, mutation evaluation, experiments and the dashboard |

---

## Features

- **Data collection:** records which lines each test covers (pytest-cov) and how long each test takes (my own pytest plugin), for 3 open-source projects
- **Kalman filter:** turns 10 noisy timing runs per test into one reliable duration estimate
- **Local search:** hill climbing with random restarts and simulated annealing, both written from scratch
- **Baselines:** cost-aware greedy and random selection
- **Exact search on small sub-suites:**
  - Uniform-cost search and A\* with my own admissible heuristic, with node counts
  - A CSP solver: plain backtracking vs. MRV + forward checking, with backtrack counts
- **Fault-detection check:** small bugs (mutants) are inserted into each project to test whether the selected tests still catch them
- **Reproducible experiments:** one command runs every method on 21 full-suite and 30 small instances with fixed seeds, and saves the tables and charts
- **Streamlit dashboard:** pick a project, a time budget and a method, then see the selected tests, coverage, time saved and comparison charts

---

## AI techniques used

| Lab | Technique | Where in the code |
|---|---|---|
| 01–02 | Python and OOP | All modules; `Optimizer` and `SearchSolver` base classes with overridden methods |
| 03 | Agents and PEAS | Utility-based agent; PEAS described in `docs/proposal.md` |
| 04 | Uniform-cost search | `src/exact_search.py`: `UniformCostSearch` |
| 05 | A\* search | `src/exact_search.py`: `AStarSearch` |
| 06 | Hill climbing, simulated annealing | `src/optimizers.py` |
| 07 | Constraint satisfaction | `src/csp.py`: `CoverCSP` |
| 09 | Kalman filter | `src/kalman.py`: `KalmanDurationEstimator` |
| 10 | Exploratory data analysis | `notebooks/eda.ipynb` |

---

## Project structure

```
test-suite-optimizer/
├── README.md
├── requirements.txt
├── .gitignore
├── docs/
│   ├── proposal.pdf / proposal.md
│   └── report.pdf / report.md
├── src/
│   ├── suite.py            # TestSuite, SelectionProblem, SelectionResult
│   ├── optimizers.py       # Random, Greedy, HillClimbing, SimulatedAnnealing
│   ├── exact_search.py     # CoverSearchProblem, UniformCostSearch, AStarSearch
│   ├── csp.py              # CoverCSP (backtracking, MRV, forward checking)
│   ├── kalman.py           # KalmanDurationEstimator
│   ├── mutation.py         # MutationEvaluator
│   ├── experiments.py      # ExperimentRunner: reproduces every result
│   ├── app.py              # Streamlit dashboard
│   └── collect/
│       ├── timing_plugin.py   # pytest plugin that records test durations
│       └── collect.py         # builds the coverage and timing CSVs
├── notebooks/
│   └── eda.ipynb
├── data/
│   ├── raw/                # not committed (.coverage files, cloned projects)
│   └── processed/          # committed CSVs: everything the code needs
└── outputs/
    ├── figures/
    └── results/
```

---

## Setup

Requires **Python 3.10 or newer**. No internet connection or API key is needed after installation.

```bash
git clone https://github.com/[your-username]/test-suite-optimizer.git
cd test-suite-optimizer

python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # macOS / Linux

pip install -r requirements.txt
```

The processed data for all three projects is already in `data/processed/`, so you don't need to collect anything to run the project.

---

## How to run

**Dashboard:**

```bash
streamlit run src/app.py
```

It opens in your browser at `http://localhost:8501`.

**Reproduce all experiments** (seeds 0–29; writes tables to `outputs/results/` and charts to `outputs/figures/`):

```bash
python -m src.experiments
```

**Optional: collect data for another project yourself.** Clone and install the target project and its test dependencies first, then run:

```bash
python -m src.collect.collect --project path/to/project --package package_name --name project_name --runs 10
```

---

## Data source

Coverage and timing data were collected by running the test suites of these open-source projects. Only derived data is stored in this repository, not their source code.

| Project | Link | Licence | Commit used |
|---|---|---|---|
| [Project 1] | [GitHub link] | [Licence] | [commit hash] |
| [Project 2] | [GitHub link] | [Licence] | [commit hash] |
| [Project 3] | [GitHub link] | [Licence] | [commit hash] |

Candidate projects: [TinyDB](https://github.com/msiemens/tinydb), [marshmallow](https://github.com/marshmallow-code/marshmallow), [Click](https://github.com/pallets/click), [toolz](https://github.com/pytoolz/toolz), [boltons](https://github.com/mahmoud/boltons).

---

## Results

*To be filled in after the experiments are run.*

| Method | Coverage at 30% budget | Mutants caught | Gap to optimum |
|---|---|---|---|
| Random | – | – | – |
| Greedy | – | – | – |
| Hill climbing | – | – | – |
| Simulated annealing | – | – | – |

---

## Known limitations

- **Line coverage only:** branch coverage and data-flow coverage are not used.
- **Pre-collected data:** selections are based on collected data, not on the latest code change. A test that covers a line is not guaranteed to catch every bug on that line.
- **Small instances only for exact search:** UCS, A\* and the CSP are run on sub-suites of 12–15 tests, because they cannot scale to full suites.
- **Simple mutation testing:** inserted bugs are simple operator changes, so the fault-detection numbers estimate real bug detection rather than measuring it.
- **No flaky-test handling:** tests whose result changes between runs are not handled.
- **Python projects only.**
- **The dashboard does not run tests live:** it reads the data in `data/processed/`.

---

## Future work

After the semester, the optimizer will be packaged as a pytest plugin (`pytest --optimize --budget=5m`), published on PyPI and offered as a GitHub Action, with test selection based on the latest code changes.

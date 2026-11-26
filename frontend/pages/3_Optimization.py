import time
from pathlib import Path

import pandas as pd
import streamlit as st
from frontend.components.theme import load_css

ROOT = Path(__file__).resolve().parents[2]

load_css()
st.title("Optimization")
st.caption("Choose an optimization algorithm and generate an efficient test suite.")

analysis = st.session_state.get("analysis_result")
analysis_path = st.session_state.get("analysis_project_path")
selected_project = st.session_state.get("selected_project_path")

if analysis is None:
    st.warning("Run project analysis before starting optimization.")
    st.page_link("pages/2_Analysis.py", label="Go to Project Analysis")
    st.stop()

if analysis_path != selected_project:
    st.warning("The selected project differs from the project analyzed.")
    st.page_link("pages/2_Analysis.py", label="Go to Analysis")
    st.stop()

original_problem = analysis["problem"]
suite = original_problem.suite

# Problem overview
st.markdown("#### Analyzed project")

st.info(
    f"**{suite.tests[0].split('::')[0] if False else selected_project}**"
)

col1, col2, col3 = st.columns(3)

col1.metric("Available tests", len(suite.tests))
col2.metric("Coverable lines", suite.total_coverable_lines())
col3.metric(
    "Full suite execution time",
    f'{suite.summary()["total_execution_time"]:.4f} s'
)

# Optimizer configuration
st.divider()
st.subheader("Configure optimization")

algorithm_options = [
    "Greedy",
    "Random Selection",
    "Hill Climbing",
    "Simulated Annealing",
    "Uniform-Cost Search"
]

with st.form("optimization_form"):

    algorithm = st.selectbox(
        "Optimization algorithm",
        options=algorithm_options,
        help="Choose the strategy used to select tests."
    )

    budget = st.number_input(
        "Execution-time budget (seconds)",
        min_value=0.01,
        value=float(original_problem.budget),
        step=0.05
    )

    st.caption(
        "The selected algorithm will attempt to maximize code coverage "
        "without exceeding this execution-time budget."
    )

    run_optimization = st.form_submit_button(
        "Run Optimization",
        type="primary",
        use_container_width=True
    )

# Run selected optimizer
if run_optimization:
    from src.core.selection_problem import SelectionProblem
    from src.algorithms.random_selection import RandomSelectionOptimizer
    from src.algorithms.greedy import GreedyOptimizer
    from src.algorithms.hill_climbing import HillClimbingOptimizer
    from src.algorithms.simulated_annealing import SimulatedAnnealingOptimizer
    from src.algorithms.search_optimization import SearchOptimizer

    problem = SelectionProblem(suite, budget)

    with st.spinner(f"Running {algorithm}..."):

        try:
            start_time = time.perf_counter()

            if algorithm == "Random Selection":
                optimizer = RandomSelectionOptimizer(
                    problem,
                    seed=42
                )

            elif algorithm == "Greedy":
                optimizer = GreedyOptimizer(problem)

            elif algorithm == "Hill Climbing":
                optimizer = HillClimbingOptimizer(problem, seed=42)

            elif algorithm == "Uniform-Cost Search":
                optimizer = SearchOptimizer(problem)
                selected_tests = optimizer.uniform_cost_search()

            else:
                optimizer = SimulatedAnnealingOptimizer(problem, seed=42)

            if algorithm != "Uniform-Cost Search":
                selected_tests = optimizer.optimize()

            runtime = time.perf_counter() - start_time

            evaluation = problem.evaluate(selected_tests)
            evaluation["optimizer_runtime_seconds"] = runtime
            evaluation["algorithm"] = algorithm
            evaluation["project_path"] = selected_project

            if algorithm == "Uniform-Cost Search":
                evaluation["nodes_expanded"] = optimizer.nodes_expanded
                evaluation["optimality_proven"] = (
                    optimizer.nodes_expanded < optimizer.max_states
                )
                evaluation["max_states"] = optimizer.max_states

            st.session_state["optimization_result"] = evaluation
            st.session_state["optimization_project_path"] = selected_project

        except Exception as error:
            st.error(f"Optimization failed: {error}")


# Display optimization results
result = st.session_state.get("optimization_result")

if (
    result is not None
    and st.session_state.get("optimization_project_path") == selected_project
):
    st.divider()
    st.subheader("Optimization results")

    st.caption(f"Algorithm: **{result['algorithm']}**")
    st.caption(
        "Live result for the selected project and budget; it is separate "
        "from the precomputed benchmark charts."
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Selected tests",
        len(result["selected_tests"]),
        delta=f'{len(suite.tests) - len(result["selected_tests"])} fewer tests'
    )

    col2.metric(
        "Code coverage",
        f'{result["coverage_percentage"]:.2f}%'
    )

    col3.metric(
        "Selected execution time",
        f'{result["total_time"]:.4f} s'
    )

    col4.metric(
        (
            "Search runtime"
            if "nodes_expanded" in result
            else "Optimizer runtime"
        ),
        f'{result["optimizer_runtime_seconds"]:.4f} s'
    )

    if result["feasible"]:
        st.success("The selected test suite satisfies the time budget.")
    else:
        st.error("The selected test suite exceeds the time budget.")

    if "nodes_expanded" in result:
        col1, col2 = st.columns(2)
        col1.metric("Nodes expanded", result["nodes_expanded"])
        col2.metric(
            "Optimality",
            "Proven" if result["optimality_proven"] else "Not proven"
        )

        if result["optimality_proven"]:
            st.success(
                "The UCS search completed; its solution is optimal for the "
                "budgeted maximum-coverage objective."
            )
        else:
            st.warning(
                "UCS reached its existing "
                f'{result["max_states"]:,}-state search limit. The returned '
                "solution is feasible, but optimality is not proven."
            )

    original_time = suite.summary()["total_execution_time"]

    saved_time = original_time - result["total_time"]

    if original_time > 0:
        saved_percentage = (saved_time / original_time) * 100
    else:
        saved_percentage = 0

    st.markdown("#### Execution time comparison")

    col1, col2 = st.columns(2)

    col1.metric(
        "Time saved",
        f"{saved_time:.4f} s"
    )

    col2.metric(
        "Execution time reduction",
        f"{saved_percentage:.2f}%"
    )

    st.markdown("#### Selected test cases")

    selected_rows = []

    for test in result["selected_tests"]:
        selected_rows.append({
            "Test": test,
            "Estimated duration (s)": round(
                suite.durations[test], 6
            ),
            "Covered lines": len(suite.coverage[test])
        })

    selected_df = pd.DataFrame(selected_rows)

    if selected_df.empty:
        st.info("The optimizer did not select any tests.")
    else:
        st.dataframe(
            selected_df,
            use_container_width=True,
            hide_index=True
        )

    st.download_button(
        "Download selected tests",
        data=selected_df.to_csv(index=False),
        file_name=f"{result['algorithm'].lower().replace(' ', '_')}_selected_tests.csv",
        mime="text/csv"
    )

elif result is None:
    st.info("Configure your algorithm and click Run Optimization.")


st.divider()
st.subheader("Saved UCS vs A* exact-instance comparison")
st.caption(
    "This precomputed comparison is separate from the live budgeted "
    "maximum-coverage run above. It uses the saved 15-test instances and "
    "the cheapest-full-coverage UCS/A* formulation."
)

exact_results_path = ROOT / "results" / "exact_small_instances.csv"

if exact_results_path.exists():
    exact_results = pd.read_csv(exact_results_path)
    project_name = Path(selected_project).name.casefold()
    project_results = exact_results[
        exact_results["project"].astype(str).str.casefold() == project_name
    ]

    if project_results.empty:
        st.info(
            "Saved exact-instance results are available for TinyDB, Toolz, "
            "and Boltons. The selected project does not match one of them."
        )
    else:
        ucs_mean_nodes = project_results[
            "fullcover_UCS_nodes_expanded"
        ].mean()
        astar_mean_nodes = project_results[
            "fullcover_AStar_nodes_expanded"
        ].mean()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric(
            "UCS mean full-cover cost",
            f'{project_results["fullcover_UCS_cost_s"].mean():.5f} s'
        )
        col2.metric(
            "A* mean full-cover cost",
            f'{project_results["fullcover_AStar_cost_s"].mean():.5f} s'
        )
        col3.metric("UCS mean nodes expanded", f"{ucs_mean_nodes:.1f}")
        col4.metric(
            "A* mean nodes expanded",
            f"{astar_mean_nodes:.1f}",
            delta=f"{ucs_mean_nodes - astar_mean_nodes:+.1f} vs UCS"
        )

        comparison_columns = {
            "instance_seed": "Instance",
            "tests": "Tests",
            "fullcover_UCS_cost_s": "UCS cost (s)",
            "fullcover_AStar_cost_s": "A* cost (s)",
            "fullcover_UCS_nodes_expanded": "UCS nodes expanded",
            "fullcover_AStar_nodes_expanded": "A* nodes expanded",
        }
        st.dataframe(
            project_results[list(comparison_columns)].rename(
                columns=comparison_columns
            ).round(6),
            use_container_width=True,
            hide_index=True
        )
        st.caption(
            f"Mean values cover {len(project_results)} saved instances. "
            "The full-coverage solution costs and node counts are reported "
            "per instance; these small-instance results are not mixed into "
            "the main optimizer benchmarks."
        )
else:
    st.warning("Saved exact small-instance results were not found.")


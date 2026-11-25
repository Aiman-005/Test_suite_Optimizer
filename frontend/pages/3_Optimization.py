import time
import streamlit as st
from frontend.components.theme import load_css

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
    "Simulated Annealing"
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

            else:
                optimizer = SimulatedAnnealingOptimizer(problem, seed=42)

            selected_tests = optimizer.optimize()

            runtime = time.perf_counter() - start_time

            evaluation = problem.evaluate(selected_tests)
            evaluation["optimizer_runtime_seconds"] = runtime
            evaluation["algorithm"] = algorithm
            evaluation["project_path"] = selected_project

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
    import pandas as pd

    st.divider()
    st.subheader("Optimization results")

    st.caption(f"Algorithm: **{result['algorithm']}**")

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
        "Optimizer runtime",
        f'{result["optimizer_runtime_seconds"]:.4f} s'
    )

    if result["feasible"]:
        st.success("The selected test suite satisfies the time budget.")
    else:
        st.error("The selected test suite exceeds the time budget.")

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


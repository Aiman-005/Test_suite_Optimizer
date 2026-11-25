from pathlib import Path
import json
import streamlit as st
from frontend.components.theme import load_css
from frontend.components.project_selection import sync_project_selection

load_css()

st.title("Project Analysis")
st.caption("Discover tests, measure execution time, and collect code coverage.")
#choosing project for analysis
registry_path = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "projects.json"
)

st.divider()
st.subheader("Choose a project to analyze")

if not registry_path.exists():
    st.warning("No registered projects found. Add a project first.")
    st.page_link("pages/1_Projects.py", label="Go to Projects")
    st.stop()

try:
    with registry_path.open("r", encoding="utf-8") as file:
        projects = json.load(file)
except (json.JSONDecodeError, OSError):
    st.error("Could not load registered projects.")
    st.stop()

if not projects:
    st.info("Register a project before starting analysis.")
    st.page_link("pages/1_Projects.py", label="Go to Projects")
    st.stop()

project_paths = [
    project["path"] for project in projects
]

selected_path = st.session_state.get("selected_project_path")

if selected_path not in project_paths:
    selected_path = project_paths[0]
    st.session_state["selected_project_path"] = selected_path

st.session_state["analysis_project_selector"] = selected_path

project_path = st.selectbox(
    "Select project",
    options=project_paths,
    format_func=lambda path: next(
        project["name"]
        for project in projects
        if project["path"] == path
    ),
    key="analysis_project_selector",
    on_change=sync_project_selection,
    args=("analysis_project_selector",)
)

project_folder = Path(project_path)

if not project_folder.is_dir():
    st.error("The selected project folder is no longer available.")
    st.stop()

st.caption(f"Project location: `{project_folder}`")

if not project_path:
    st.warning("No project selected. Register and select a project first.")
    st.page_link("pages/1_Projects.py", label="Go to Projects")
    st.stop()

project_folder = Path(project_path)

if not project_folder.is_dir():
    st.error("The selected project folder is no longer available.")
    st.stop()

st.markdown("#### Selected project")
st.info(f"**{project_folder.name}**  \n`{project_folder}`")
# Analysis configuration

st.divider()
st.subheader("Analysis configuration")

default_timing_path = (
    Path("data/processed")
    / f"{project_folder.name.lower()}_kalman_estimates.csv"
)

if default_timing_path.is_file():
    default_timing_value = str(default_timing_path.resolve())
else:
    default_timing_value = ""

with st.form("analysis_configuration"):
    budget = st.number_input(
        "Optimization time budget (seconds)",
        min_value=0.01,
        value=1.0,
        step=0.1,
        help="The maximum execution time allowed for the selected test suite."
    )

    timing_path = st.text_input(
        "Kalman estimates CSV (optional)",
        value=default_timing_value,
        placeholder="Leave empty to use measured execution times",
        help="Provide a timing CSV that belongs to this project."
    )

    run_analysis = st.form_submit_button(
        "Run Analysis",
        type="primary",
        use_container_width=True
    )

# Run analysis

if run_analysis:
    try:
        from src.app.project_analyzer import analyze_project
        with st.spinner(
            "Analyzing project... Discovering tests, executing them, "
            "and collecting coverage. This may take some time."
        ):
            result = analyze_project(
                project_path=project_path,
                budget=budget,
                timing_estimates_path=(
                    timing_path.strip() if timing_path.strip() else None
                )
            )

        st.session_state["analysis_result"] = result
        st.session_state["analysis_project_path"] = str(project_folder.resolve())
        st.session_state["analysis_budget"] = budget

        st.success("Project analysis completed successfully.")

    except Exception as error:
        st.error(f"Analysis failed: {error}")

# Display saved analysis

result = st.session_state.get("analysis_result")
analyzed_path = st.session_state.get("analysis_project_path")

if result is not None:
    import pandas as pd
    if analyzed_path != str(project_folder.resolve()):
        st.warning(
            "The saved analysis belongs to a different project. "
            "Run analysis again for the currently selected project."
        )
        st.stop()

    problem = result["problem"]
    execution = result["execution_result"]
    coverage_result = result["coverage_result"]
    summary = result["suite_summary"]

    st.divider()
    st.subheader("Analysis overview")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Discovered tests", result["discovered_tests"])
    col2.metric("Included tests", result["included_tests"])
    col3.metric("Excluded tests", len(result["excluded_tests"]))
    col4.metric("Coverable lines", summary["total_coverable_lines"])

    st.markdown("#### Test execution")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Passed", execution["passed"])
    col2.metric("Failed", execution["failed"])
    col3.metric("Skipped", execution["skipped"])
    col4.metric(
        "Not run",
        execution["total_tests"]
        - execution["passed"]
        - execution["failed"]
        - execution["skipped"]
    )

    st.markdown("#### Timing and coverage")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Full suite execution time",
        f'{summary["total_execution_time"]:.4f} s'
    )

    col2.metric(
        "Tests with coverage",
        coverage_result["tests_with_coverage"]
    )

    col3.metric(
        "Optimization budget",
        f'{problem.budget:.4f} s'
    )

    duration_label = (
        "Kalman estimates"
        if result["duration_source"] == "kalman_estimates"
        else "Measured execution times"
    )

    st.caption(f"Duration source: **{duration_label}**")

    st.divider()
    st.subheader("Test details")

    execution_rows = []

    coverage_by_id = coverage_result["coverage"]

    for item in execution["results"]:
        node_id = item["node_id"]

        execution_rows.append({
            "Test": node_id,
            "Status": item["status"].replace("_", " ").title(),
            "Execution time (s)": round(item["duration_seconds"], 6),
            "Covered lines": sum(
                len(lines)
                for lines in coverage_by_id.get(node_id, {}).values()
            )
        })

    details_df = pd.DataFrame(execution_rows)

    st.dataframe(
        details_df,
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "Download test analysis CSV",
        data=details_df.to_csv(index=False),
        file_name=f"{project_folder.name}_analysis.csv",
        mime="text/csv"
    )

    if result["excluded_tests"]:
        with st.expander(
            f"Excluded tests ({len(result['excluded_tests'])})"
        ):
            st.write(result["excluded_tests"])

    st.divider()

    st.markdown("#### Ready for optimization")

    st.write(
        f"Your optimization problem contains **{result['included_tests']} "
        f"tests**, with a time budget of **{problem.budget:.4f} seconds**."
    )

    st.success("Analysis data is ready for the Optimization page.")

else:
    st.info(
        "No analysis results yet. Configure your time budget and click "
        "'Run Analysis' to begin."
    )


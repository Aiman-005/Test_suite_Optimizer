from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
from frontend.components.mutation_results import add_mutant_count_columns
from frontend.components.theme import load_css

ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_FILE = ROOT / "results" / "combined_benchmark.csv"
DATA_DIR = ROOT / "data" / "processed"

# DATA

def load_benchmarks():
    if not BENCHMARK_FILE.exists():
        return pd.DataFrame()

    df = pd.read_csv(BENCHMARK_FILE)

    # Standardize data types
    numeric_columns = [
        "selected_tests",
        "selected_execution_time",
        "coverage_percentage",
        "optimizer_runtime_seconds",
        "budget_seconds",
    ]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    df["feasible"] = (
        df["feasible"]
        .astype(str)
        .str.lower()
        .map({"true": True, "false": False})
    )

    return df


def load_mutant_counts(project):
    project_key = project.lower()
    mutants_file = DATA_DIR / f"{project_key}_mutants.csv"
    kill_matrix_file = DATA_DIR / f"{project_key}_kill_matrix.csv"

    if not mutants_file.exists() or not kill_matrix_file.exists():
        return None

    mutants = pd.read_csv(mutants_file, usecols=["mutant_id"])
    kill_matrix = pd.read_csv(kill_matrix_file, usecols=["mutant_id"])
    return (
        mutants["mutant_id"].nunique(),
        kill_matrix["mutant_id"].nunique(),
    )


# PAGE SETUP

load_css()


def apply_chart_theme(fig):
    is_light = (
        getattr(st.context, "theme", {}).get(
            "base",
            getattr(st.context, "theme", {}).get("type", "dark")
        ) == "light"
    )

    font_color = "#172033" if is_light else "#EDF2FA"
    grid_color = (
        "rgba(100,116,139,0.18)"
        if is_light
        else "rgba(148,163,184,0.18)"
    )

    fig.update_layout(
        template="plotly_white" if is_light else "plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=font_color),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
        ),
        margin=dict(l=25, r=25, t=35, b=25),
    )

    fig.update_xaxes(
        gridcolor=grid_color,
        zerolinecolor=grid_color,
    )

    fig.update_yaxes(
        gridcolor=grid_color,
        zerolinecolor=grid_color,
    )

    return fig


st.title("Results & Comparison")

st.caption(
    "Benchmark charts and records use one run per optimizer at 50% of "
    "the full-suite estimated time (seed 42). Live Optimization runs use "
    "your selected budget and are not part of this benchmark."
)

df = load_benchmarks()

if df.empty:
    st.warning("No benchmark data found.")
    st.stop()

# FILTERS

st.markdown("### Benchmark Filters")

col1, col2 = st.columns(2)

with col1:
    selected_project = st.selectbox(
        "Select Project",
        ["All Projects"] + sorted(df["project"].dropna().unique().tolist()),
    )

with col2:
    selected_optimizer = st.selectbox(
        "Select Optimizer",
        ["All Optimizers"] + sorted(df["optimizer"].dropna().unique().tolist()),
    )

filtered_df = df.copy()

if selected_project != "All Projects":
    filtered_df = filtered_df[
        filtered_df["project"] == selected_project
    ]

if selected_optimizer != "All Optimizers":
    filtered_df = filtered_df[
        filtered_df["optimizer"] == selected_optimizer
    ]

if filtered_df.empty:
    st.info("No benchmark records match the selected filters.")
    st.stop()

# KPI SUMMARY

st.markdown("### Performance Overview")

average_coverage = filtered_df["coverage_percentage"].mean()

average_execution = filtered_df[
    "selected_execution_time"
].mean()

average_runtime = filtered_df[
    "optimizer_runtime_seconds"
].mean()

feasible_count = filtered_df["feasible"].eq(True).sum()

total_records = len(filtered_df)

best_record = filtered_df.loc[
    filtered_df["coverage_percentage"].idxmax()
]

k1, k2, k3, k4 = st.columns(4)

with k1:
    st.metric(
        "Average Coverage",
        f"{average_coverage:.2f}%",
    )

with k2:
    st.metric(
        "Avg. Test Execution",
        f"{average_execution:.4f}s",
    )

with k3:
    st.metric(
        "Avg. Optimizer Runtime",
        f"{average_runtime:.4f}s",
    )

with k4:
    st.metric(
        "Feasible Runs",
        f"{feasible_count}/{total_records}",
    )

st.divider()

# BEST PERFORMER
st.markdown("### Highest Coverage Result") 
best_col1, best_col2, best_col3 = st.columns(3)

best_col1.metric(
    "Project",
    best_record["project"],
)

best_col2.metric(
    "Optimizer",
    best_record["optimizer"],
)

best_col3.metric(
    "Coverage Achieved",
    f"{best_record['coverage_percentage']:.2f}%",
)

st.caption(
    "Best result is determined by highest coverage among the currently filtered records."
)

st.divider()

# COVERAGE COMPARISON
st.markdown("### Coverage Comparison")

coverage_fig = px.bar(
    filtered_df,
    x="optimizer",
    y="coverage_percentage",
    color="project",
    barmode="group",
    text_auto=".2f",
    labels={
        "optimizer": "Optimizer",
        "coverage_percentage": "Coverage (%)",
        "project": "Project",
    },
)

coverage_fig.update_layout(
    template=(
        "plotly"
        if getattr(st.context, "theme", {}).get(
            "base",
            getattr(st.context, "theme", {}).get("type", "dark")
        ) == "light"
        else "plotly_dark"
    ),
    height=420,
    margin=dict(l=20, r=20, t=30, b=20),
    legend_title_text="Project",
)

coverage_fig.update_yaxes(
    range=[0, 105],
    ticksuffix="%",
)

apply_chart_theme(coverage_fig)
st.plotly_chart(
    coverage_fig,
    width="stretch",
    config={
        "displaylogo": False,
        "responsive": True,
    },
)

# SELECTED TESTS

st.markdown("### Selected Test Cases")

if filtered_df["selected_tests"].notna().any():

    selected_fig = px.bar(
        filtered_df.dropna(subset=["selected_tests"]),
        x="optimizer",
        y="selected_tests",
        color="project",
        barmode="group",
        text_auto=True,
        labels={
            "optimizer": "Optimizer",
            "selected_tests": "Selected Tests",
            "project": "Project",
        },
    )

    selected_fig.update_layout(
        template=(
            "plotly"
            if getattr(st.context, "theme", {}).get(
                "base",
                getattr(st.context, "theme", {}).get("type", "dark")
            ) == "light"
            else "plotly_dark"
        ),
        height=400,
        margin=dict(l=20, r=20, t=30, b=20),
    )
    apply_chart_theme(selected_fig)

    st.plotly_chart(
        selected_fig,
        width="stretch",
        config={"displaylogo": False, "responsive": True},
    )

else:
    st.info("Selected test counts are unavailable for these records.")

st.caption(
    "Missing selected-test counts are excluded from this chart, not treated as zero."
)

st.divider()

# EXECUTION TIME VS OPTIMIZER RUNTIME
st.markdown("### Execution & Optimization Performance")

time_fig = px.bar(
    filtered_df,
    x="optimizer",
    y="selected_execution_time",
    color="project",
    barmode="group",
    text_auto=".4f",
    labels={
        "optimizer": "Optimizer",
        "selected_execution_time": "Test Execution Time (seconds)",
        "project": "Project",
    },
)

time_fig.update_layout(
    template=(
        "plotly"
        if getattr(st.context, "theme", {}).get(
            "base",
            getattr(st.context, "theme", {}).get("type", "dark")
        ) == "light"
        else "plotly_dark"
    ),
    height=400,
    margin=dict(l=20, r=20, t=30, b=20),
)
apply_chart_theme(time_fig)
st.plotly_chart(
    time_fig,
    width="stretch",
    config={"displaylogo": False, "responsive": True},
)

runtime_fig = px.bar(
    filtered_df,
    x="optimizer",
    y="optimizer_runtime_seconds",
    color="project",
    barmode="group",
    text_auto=".4f",
    labels={
        "optimizer": "Optimizer",
        "optimizer_runtime_seconds": "Optimizer Runtime (seconds)",
        "project": "Project",
    },
)

runtime_fig.update_layout(
    template=(
        "plotly"
        if getattr(st.context, "theme", {}).get(
            "base",
            getattr(st.context, "theme", {}).get("type", "dark")
        ) == "light"
        else "plotly_dark"
    ),
    height=400,
    margin=dict(l=20, r=20, t=30, b=20),
)

apply_chart_theme(runtime_fig)
st.plotly_chart(
    runtime_fig,
    width="stretch",
    config={"displaylogo": False, "responsive": True},
)

st.divider()

# DETAILED BENCHMARK TABLE

st.markdown("### Detailed Benchmark Records")

display_columns = [
    "project",
    "optimizer",
    "selected_tests",
    "selected_execution_time",
    "coverage_percentage",
    "mutants_caught_percentage",
    "feasible",
    "optimizer_runtime_seconds",
    "budget_seconds",
]

available_columns = [
    column for column in display_columns
    if column in filtered_df.columns
]

display_df = filtered_df[available_columns].copy()

display_df = display_df.rename(
    columns={
        "project": "Project",
        "optimizer": "Optimizer",
        "selected_tests": "Selected Tests",
        "selected_execution_time": "Execution Time (s)",
        "coverage_percentage": "Coverage (%)",
        "mutants_caught_percentage": "Detectable Mutants Caught (%)",
        "feasible": "Feasible",
        "optimizer_runtime_seconds": "Optimizer Runtime (s)",
        "budget_seconds": "Budget (s)",
    }
)

st.dataframe(
    display_df,
    width="stretch",
    hide_index=True,
    column_config={
        "Selected Tests": st.column_config.NumberColumn(
            "Selected Tests",
            format="%d",
        ),
        "Execution Time (s)": st.column_config.NumberColumn(
            "Execution Time (s)",
            format="%.4f",
        ),
        "Coverage (%)": st.column_config.NumberColumn(
            "Coverage (%)",
            format="%.2f%%",
        ),
        "Detectable Mutants Caught (%)": st.column_config.NumberColumn(
            "Detectable Mutants Caught (%)",
            format="%.2f%%",
        ),
        "Optimizer Runtime (s)": st.column_config.NumberColumn(
            "Optimizer Runtime (s)",
            format="%.4f",
        ),
        "Budget (s)": st.column_config.NumberColumn(
            "Budget (s)",
            format="%.4f",
        ),
    },
)

# Downloads filtered benchmark data
csv_data = filtered_df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download Benchmark Data",
    data=csv_data,
    file_name="tso_benchmark_results.csv",
    mime="text/csv",
)

st.caption(
    "Results are based on the recorded benchmark experiments for TinyDB, Toolz, and Boltons."
)


# COMPARE AT A CHOSEN TIME BUDGET
# Uses the pre-collected budget sweep from run_experiments.py
# (7 budgets x 30 seeds); no tests are run here.

SWEEP_FILE = ROOT / "results" / "budget_sweep.csv"


def load_budget_sweep():
    if not SWEEP_FILE.exists():
        return pd.DataFrame()
    return pd.read_csv(SWEEP_FILE)


st.divider()
st.markdown("### Compare Methods at a Time Budget")
st.caption(
    "Pick a project and a time budget (as a share of the full suite's run time). "
    "Values are means over 30 seeds from the pre-collected experiment; "
    "greedy is deterministic. Detectable Mutants Caught (%) is the share of "
    "mutants killed by the full suite that the selected tests still kill."
)

sweep = load_budget_sweep()

if sweep.empty:
    st.info("Budget sweep not found. Run `python run_experiments.py` to create it.")
else:
    budget_col1, budget_col2 = st.columns(2)

    with budget_col1:
        sweep_project = st.selectbox(
            "Project",
            sorted(sweep["project"].unique().tolist()),
            key="sweep_project",
        )

    budget_options = sorted(sweep["budget_fraction"].unique().tolist())

    with budget_col2:
        sweep_budget = st.select_slider(
            "Time budget",
            options=budget_options,
            value=0.05 if 0.05 in budget_options else budget_options[0],
            format_func=lambda b: f"{b:.0%}",
            key="sweep_budget",
        )

    # Full-suite time: the main benchmark uses a 50% budget.
    full_suite_seconds = (
        df.loc[df["project"] == sweep_project, "budget_seconds"].iloc[0] / 0.5
        if (df["project"] == sweep_project).any() else None
    )

    at_budget = (
        sweep[
            (sweep["project"] == sweep_project)
            & (sweep["budget_fraction"] == sweep_budget)
        ]
        .groupby("optimizer")
        .agg(
            mean_coverage=("coverage_percentage", "mean"),
            std_coverage=("coverage_percentage", "std"),
            best_coverage=("coverage_percentage", "max"),
            bugs_caught=("mutants_caught_percentage", "mean"),
            tests_selected=("selected_tests", "mean"),
            time_used=("selected_execution_time", "mean"),
            runtime=("optimizer_runtime_seconds", "mean"),
            runs=("seed", "count"),
        )
        .reset_index()
        .sort_values("mean_coverage", ascending=False)
    )
    at_budget["std_coverage"] = at_budget["std_coverage"].fillna(0.0)

    if full_suite_seconds:
        at_budget["time_saved"] = (
            100 * (1 - at_budget["time_used"] / full_suite_seconds)
        )

    best_row = at_budget.iloc[0]
    greedy_row = at_budget[at_budget["optimizer"] == "Greedy"]

    m1, m2, m3 = st.columns(3)
    m1.metric("Best method", best_row["optimizer"])
    m2.metric("Best mean coverage", f'{best_row["mean_coverage"]:.2f}%')
    if not greedy_row.empty:
        m3.metric(
            "Gain over greedy",
            f'{best_row["mean_coverage"] - greedy_row["mean_coverage"].iloc[0]:+.2f} pts',
        )

    budget_fig = px.bar(
        at_budget,
        x="optimizer",
        y="mean_coverage",
        error_y="std_coverage",
        color="optimizer",
        text_auto=".2f",
        labels={"optimizer": "Optimizer", "mean_coverage": "Mean coverage (%)"},
    )
    budget_fig.update_layout(height=400, showlegend=False)
    budget_fig.update_yaxes(range=[0, 105], ticksuffix="%")
    apply_chart_theme(budget_fig)
    st.plotly_chart(
        budget_fig,
        width="stretch",
        config={"displaylogo": False, "responsive": True},
    )

    table = at_budget.rename(columns={
        "optimizer": "Optimizer",
        "mean_coverage": "Mean Coverage (%)",
        "std_coverage": "Std Dev (pts)",
        "best_coverage": "Best Coverage (%)",
        "bugs_caught": "Detectable Mutants Caught (%)",
        "tests_selected": "Tests Selected",
        "time_used": "Time Used (s)",
        "time_saved": "Time Saved vs Full Suite (%)",
        "runtime": "Optimizer Runtime (s)",
        "runs": "Runs",
    })
    st.dataframe(
        table,
        hide_index=True,
        width="stretch",
        column_config={
            "Mean Coverage (%)": st.column_config.NumberColumn(format="%.2f"),
            "Std Dev (pts)": st.column_config.NumberColumn(format="%.2f"),
            "Best Coverage (%)": st.column_config.NumberColumn(format="%.2f"),
            "Detectable Mutants Caught (%)": st.column_config.NumberColumn(
                format="%.2f"
            ),
            "Tests Selected": st.column_config.NumberColumn(format="%.1f"),
            "Time Used (s)": st.column_config.NumberColumn(format="%.4f"),
            "Time Saved vs Full Suite (%)": st.column_config.NumberColumn(format="%.1f"),
            "Optimizer Runtime (s)": st.column_config.NumberColumn(format="%.3f"),
        },
    )

    st.markdown("#### Coverage Across All Budgets")
    curve = (
        sweep[sweep["project"] == sweep_project]
        .groupby(["budget_fraction", "optimizer"])["coverage_percentage"]
        .mean()
        .reset_index()
    )
    curve["budget_percent"] = curve["budget_fraction"] * 100

    curve_fig = px.line(
        curve,
        x="budget_percent",
        y="coverage_percentage",
        color="optimizer",
        markers=True,
        log_x=True,
        labels={
            "budget_percent": "Time budget (% of full suite, log scale)",
            "coverage_percentage": "Mean coverage (%)",
            "optimizer": "Optimizer",
        },
    )
    curve_fig.add_vline(
        x=sweep_budget * 100, line_dash="dot", line_color="gray",
        annotation_text="selected budget",
    )
    curve_fig.update_layout(height=420)
    curve_fig.update_yaxes(ticksuffix="%")
    apply_chart_theme(curve_fig)
    st.plotly_chart(
        curve_fig,
        width="stretch",
        config={"displaylogo": False, "responsive": True},
    )

    st.divider()
    st.markdown("### Fault Detection & Mutants Caught")

    mutant_counts = load_mutant_counts(sweep_project)
    if mutant_counts is None:
        st.info(
            f"Mutation results are unavailable for {sweep_project}; "
            "both the sampled-mutant file and kill matrix are required."
        )
    else:
        total_mutants, detectable_mutants = mutant_counts
        if total_mutants == 0 or detectable_mutants == 0:
            st.info(
                f"Mutation detection counts are unavailable for {sweep_project}: "
                "the sampled-mutant file or full-suite kill matrix has no mutants."
            )
        else:
            project_sweep = sweep[sweep["project"] == sweep_project]
            fault_sweep = add_mutant_count_columns(
                project_sweep,
                total_mutants=total_mutants,
                detectable_mutants=detectable_mutants,
            )
            fault_at_budget = (
                fault_sweep[fault_sweep["budget_fraction"] == sweep_budget]
                .groupby("optimizer")
                .agg(
                    mutants_caught=("mutants_caught_count", "mean"),
                    mutants_survived=("mutants_survived_count", "mean"),
                    detection_percentage=("mutant_detection_percentage", "mean"),
                )
                .reset_index()
            )

            if fault_at_budget.empty:
                st.info(
                    "No mutant-detection records match the selected project "
                    "and budget."
                )
            else:
                metric_optimizer = st.selectbox(
                    "Optimizer for mutant metrics",
                    sorted(fault_at_budget["optimizer"].tolist()),
                    key="fault_optimizer",
                )
                metric_row = fault_at_budget[
                    fault_at_budget["optimizer"] == metric_optimizer
                ].iloc[0]
                mutant_col1, mutant_col2, mutant_col3, mutant_col4 = st.columns(4)
                mutant_col1.metric("Total Mutants", total_mutants)
                mutant_col2.metric(
                    "Mean Mutants Caught",
                    f'{metric_row["mutants_caught"]:.1f}',
                )
                mutant_col3.metric(
                    "Mean Mutants Survived",
                    f'{metric_row["mutants_survived"]:.1f}',
                )
                mutant_col4.metric(
                    "Mutant Detection (%)",
                    f'{metric_row["detection_percentage"]:.2f}%',
                )

                st.caption(
                    "Counts and detection percentages use all sampled mutants; "
                    "mutants not killed by the full suite count as survived. "
                    "Values are means across stored seeds (Greedy has one run)."
                )

                fault_curve = (
                    fault_sweep.groupby(["budget_fraction", "optimizer"])
                    ["mutants_caught_count"]
                    .mean()
                    .reset_index(name="mean_mutants_caught")
                )
                fault_curve["budget_percent"] = (
                    fault_curve["budget_fraction"] * 100
                )
                fault_fig = px.line(
                    fault_curve,
                    x="budget_percent",
                    y="mean_mutants_caught",
                    color="optimizer",
                    markers=True,
                    log_x=True,
                    labels={
                        "budget_percent": (
                            "Time Budget (% of Full Suite, log scale)"
                        ),
                        "mean_mutants_caught": "Mean Mutants Caught",
                        "optimizer": "Optimizer",
                    },
                )
                fault_fig.add_vline(
                    x=sweep_budget * 100,
                    line_dash="dot",
                    line_color="gray",
                    annotation_text="selected budget",
                )
                fault_fig.update_layout(height=420)
                fault_fig.update_yaxes(range=[0, total_mutants])
                apply_chart_theme(fault_fig)
                st.plotly_chart(
                    fault_fig,
                    width="stretch",
                    config={"displaylogo": False, "responsive": True},
                )

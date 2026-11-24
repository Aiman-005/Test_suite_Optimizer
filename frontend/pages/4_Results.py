from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
from frontend.components.theme import load_css

ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_FILE = ROOT / "results" / "combined_benchmark.csv"

# DATA

@st.cache_data
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
    "Evaluate optimizer performance across real-world Python projects."
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

# Download filtered benchmark data
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

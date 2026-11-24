from pathlib import Path
from frontend.components.theme import load_css
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
BENCHMARK_FILE = ROOT / "results" / "combined_benchmark.csv"

load_css()

@st.cache_data
def load_benchmarks():
    if not BENCHMARK_FILE.exists():
        return pd.DataFrame()

    return pd.read_csv(BENCHMARK_FILE)


def metric_card(label, value, note):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_heading(title, caption):
    st.markdown(
        f"""
        <div class="section-heading">{title}</div>
        <div class="section-caption">{caption}</div>
        """,
        unsafe_allow_html=True,
    )

df = load_benchmarks()

# Sidebar
# Shared application sidebar

# Hero
st.markdown(
    """
    <div class="hero">
        <div class="eyebrow">INTELLIGENT TEST SELECTION PLATFORM</div>
        <div class="hero-title">
            Run less. <span>Cover more.</span>
        </div>
        <div class="hero-subtitle">
            Analyze test suites, optimize execution budgets, and preserve
            code coverage with intelligent test selection.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if df.empty:
    st.warning(
        "Benchmark data was not found. Expected results/combined_benchmark.csv."
    )
    st.stop()

required = {
    "project",
    "optimizer",
    "coverage_percentage",
    "feasible",
    "optimizer_runtime_seconds",
}

missing = required - set(df.columns)

if missing:
    st.error(f"Benchmark CSV is missing columns: {', '.join(sorted(missing))}")
    st.stop()

# Summary calculations
projects = sorted(df["project"].dropna().unique())
optimizers = sorted(df["optimizer"].dropna().unique())
avg_coverage = df["coverage_percentage"].mean()
feasible_runs = df["feasible"].astype(str).str.lower().isin(
    ["true", "1", "yes"]
).sum()

c1, c2, c3, c4 = st.columns(4)

with c1:
    metric_card("PROJECTS ANALYZED", str(len(projects)), "Real-world Python projects")

with c2:
    metric_card("OPTIMIZERS", str(len(optimizers)), "Selection strategies compared")

with c3:
    metric_card("AVERAGE COVERAGE", f"{avg_coverage:.1f}%", "Across benchmark runs")

with c4:
    metric_card("FEASIBLE RUNS", f"{feasible_runs}/{len(df)}", "Within execution budgets")

# Coverage chart
section_heading(
    "Optimization performance",
    "Code coverage achieved by each optimizer across the benchmark projects.",
)

coverage = (
    df.groupby(["project", "optimizer"], as_index=False)
    ["coverage_percentage"]
    .mean()
)

fig = px.bar(
    coverage,
    x="project",
    y="coverage_percentage",
    color="optimizer",
    barmode="group",
    template=(
    "plotly"
    if getattr(st.context, "theme", {}).get("base",
        getattr(st.context, "theme", {}).get("type", "dark")
    ) == "light"
    else "plotly_dark"
    ),
    color_discrete_sequence=[
        "#8b7cff",
        "#43d9e8",
        "#f5b85c",
        "#45d6a0", 
        "#e879a9",
    ],
    labels={
        "project": "Project",
        "coverage_percentage": "Coverage (%)",
        "optimizer": "Optimizer",
    },
)

fig.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans", color=("#334155" if getattr(st.context, "theme", {}).get("type", "dark") == "light" else "#cbd5e1")),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
    ),
    margin=dict(l=15, r=15, t=35, b=15),
    height=370,
    yaxis=dict(range=[0, 105], gridcolor="rgba(148,163,184,0.12)"),
    xaxis=dict(showgrid=False),
)

fig.update_traces(
    marker_line_width=0,
    hovertemplate="%{x}<br>Coverage: %{y:.2f}%<extra></extra>",
)


# Regular chart
chart_config = {
    "displayModeBar": True,
    "displaylogo": False,
    "responsive": True,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
}

st.plotly_chart(fig, width="stretch", config=chart_config)

# Project overview
section_heading(
    "Your benchmark projects",
    "Real open-source repositories used to evaluate the optimizer.",
)

columns = st.columns(len(projects))

for column, project in zip(columns, projects):
    project_data = df[df["project"] == project]
    project_coverage = project_data["coverage_percentage"].max()

    with column:
        st.markdown(
            f"""
            <div class="project-card">
                <div class="project-name">{project.title()}</div>
                <div class="project-meta">
                    <span class="status-dot"></span>Benchmark completed
                </div>
                <div style="margin-top:1.1rem;font-size:1.65rem;
                            font-family:'Space Grotesk';font-weight:700;
                            color:var(--text);">
                    {project_coverage:.1f}%
                </div>
                <div class="project-meta">Best recorded coverage</div>
                <div class="project-meta">
                    {project_data['optimizer'].nunique()} optimizers evaluated
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown("")
st.caption(
    "TEST SUITE OPTIMIZER Â· Benchmark overview Â· Data from combined_benchmark.csv"
)



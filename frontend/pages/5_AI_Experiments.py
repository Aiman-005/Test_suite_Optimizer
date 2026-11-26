from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
from frontend.components.theme import load_css
from src.ai_demos.markov_model import run_markov_experiment

ROOT = Path(__file__).resolve().parents[2]
ML_DIR = ROOT / "results" / "ml"
DATA_DIR = ROOT / "data" / "processed"

load_css()

st.title("AI Experiments")
st.caption(
    "Supporting experiments in duration estimation "
    "and unsupervised test-case clustering."
)


def read_csv(path):
    if not path.exists():
        return None

    return pd.read_csv(path)


def show_left_aligned_table(dataframe):
    column_config = {}

    for column in dataframe.columns:
        if pd.api.types.is_numeric_dtype(dataframe[column]):
            column_config[column] = st.column_config.NumberColumn(
                alignment="left"
            )

    st.dataframe(
        dataframe,
        column_config=column_config,
        use_container_width=True,
        hide_index=True
    )


def apply_dark_theme(fig):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#E5E7EB",
        margin=dict(l=20, r=20, t=60, b=20)
    )
    return fig


PROJECTS = {
    "TinyDB": "tinydb",
    "Toolz": "toolz",
    "Boltons": "boltons"
}


# K-MEANS CLUSTERING
st.header("K-Means Clustering")

st.write(
    "Tests are grouped using estimated execution duration "
    "and the number of covered source lines. Both features are "
    "log-scaled and standardized before clustering, so a few very "
    "slow tests do not dominate the distances."
)

cross_summary = read_csv(
    ML_DIR / "kmeans_cross_project_summary.csv"
)

if cross_summary is not None:

    st.subheader("Cross-Project Comparison")

    cols = st.columns(3)

    for col, (_, row) in zip(
        cols,
        cross_summary.iterrows()
    ):
        with col:
            st.metric(
                label=row["project"].title(),
                value=f'{int(row["selected_clusters"])} clusters',
                delta=f'Silhouette: {row["silhouette_score"]:.4f}'
            )

    display_summary = cross_summary.copy()

    if "silhouette_score" in display_summary.columns:
        display_summary["silhouette_score"] = (
            display_summary["silhouette_score"].round(4)
        )

    show_left_aligned_table(display_summary)

else:
    st.warning("Cross-project K-Means summary was not found.")


st.divider()

selected_project = st.selectbox(
    "Select project",
    list(PROJECTS.keys())
)

project_key = PROJECTS[selected_project]

metrics = read_csv(
    ML_DIR / f"{project_key}_kmeans_metrics.csv"
)

clusters = read_csv(
    ML_DIR / f"{project_key}_kmeans_cluster_summary.csv"
)

cluster_data = read_csv(
    ML_DIR / f"{project_key}_kmeans_clusters.csv"
)


if metrics is not None and not metrics.empty:

    best_row = metrics.loc[
        metrics["silhouette_score"].idxmax()
    ]

    if cross_summary is not None:
        project_summary = cross_summary[
            cross_summary["project"].str.lower() == project_key
        ]

        clustered_count = (
            int(project_summary.iloc[0]["total_tests_clustered"])
            if not project_summary.empty
            else "N/A"
        )
    else:
        clustered_count = "N/A"

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Selected clusters",
        int(best_row["n_clusters"])
    )

    col2.metric(
        "Best silhouette score",
        f'{best_row["silhouette_score"]:.4f}'
    )

    col3.metric(
        "Tests clustered",
        clustered_count
    )

    # INTERACTIVE CLUSTER VISUALIZATION

    st.subheader(f"{selected_project} Cluster Visualization")

    if cluster_data is not None and not cluster_data.empty:

        scatter = px.scatter(
            cluster_data,
            x="kalman_estimate_seconds",
            y="covered_line_count",
            color="cluster",
            hover_data=["test_node_id"],
            labels={
                "kalman_estimate_seconds":
                    "Estimated Execution Duration (seconds)",
                "covered_line_count":
                    "Number of Covered Source Lines",
                "cluster": "Cluster"
            },
            title=f"{selected_project} Test Clusters"
        )

        apply_dark_theme(scatter)

        st.plotly_chart(
            scatter,
            use_container_width=True
        )

    else:
        st.info("Cluster data not found.")

    # CLUSTER EVALUATION
    st.subheader("Cluster Evaluation")

    show_left_aligned_table(metrics.round(4))

    # CLUSTER CHARACTERISTICS

    if clusters is not None:

        st.subheader("Cluster Characteristics")

        display_clusters = clusters.copy()

        display_clusters["cluster"] = (
            "Cluster " + display_clusters["cluster"].astype(str)
        )

        show_left_aligned_table(display_clusters.round(4))

else:
    st.warning("K-Means metrics for this project were not found.")

# KALMAN FILTER
st.divider()

st.header("Kalman Filter Duration Estimation")

st.write(
    "The Kalman Filter processes repeated execution-time "
    "measurements to maintain an updated estimate of each "
    "test's execution duration. These estimates are used "
    "by the test-selection experiments."
)

timing = read_csv(
    DATA_DIR / f"{project_key}_kalman_estimates.csv"
)

if timing is not None and not timing.empty:

    duration_column = next(
        (
            column for column in [
                "kalman_estimate_seconds",
                "estimated_duration"
            ]
            if column in timing.columns
        ),
        None
    )

    if duration_column is not None:

        timing = timing.dropna(
            subset=[duration_column]
        )

        timing = timing[
            timing[duration_column] > 0
        ]

        durations = timing[duration_column]

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Tests estimated",
            len(timing)
        )

        col2.metric(
            "Average estimated duration",
            f"{durations.mean():.5f} s"
        )

        col3.metric(
            "Median estimated duration",
            f"{durations.median():.5f} s"
        )

        # DURATION DISTRIBUTION
        st.subheader("Estimated Duration Distribution")

        histogram = px.histogram(
            timing,
            x=duration_column,
            nbins=25,
            labels={
                duration_column:
                    "Estimated Duration (seconds)",
                "count": "Number of Tests"
            },
            title=f"{selected_project} Test Duration Distribution"
        )

        apply_dark_theme(histogram)

        st.plotly_chart(
            histogram,
            use_container_width=True
        )

        # DURATION ESTIMATES TABLE
        st.subheader("Test Duration Estimates")

        display_columns = [
            column for column in [
                "test_node_id",
                "node_id",
                "raw_mean_seconds",
                "kalman_estimate_seconds",
                "estimated_duration",
                "measurements"
            ]
            if column in timing.columns
        ]

        show_left_aligned_table(
            timing[display_columns].round(6)
        )

    else:
        st.warning(
            "Could not identify the estimated-duration column."
        )

else:
    st.warning(
        "Kalman duration estimates for this project were not found."
    )

# MARKOV MODEL
st.divider()

st.header("Markov Model Test Duration States")

st.write(
    "This separate experiment classifies recorded execution times as Fast, "
    "Medium, or Slow, then estimates the probability of the next state from "
    "consecutive runs. State boundaries and transitions are learned only "
    "from runs 1–8; predictions are evaluated on each test's held-out "
    "run-9-to-10 transition."
)

markov_timing = read_csv(
    DATA_DIR / f"{project_key}_timing_runs.csv"
)

if markov_timing is not None and not markov_timing.empty:
    markov_result = run_markov_experiment(markov_timing)

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Training transitions",
        markov_result.training_transitions
    )
    col2.metric(
        "Held-out predictions",
        markov_result.held_out_predictions
    )
    col3.metric(
        "Held-out accuracy",
        f"{markov_result.accuracy:.1%}",
        delta=(
            f"{markov_result.accuracy - markov_result.baseline_accuracy:+.1%}"
            " vs majority baseline"
        )
    )

    state_counts = ", ".join(
        f"{state} {count}"
        for state, count in markov_result.state_counts.items()
    )
    st.caption(
        f"Majority-state baseline: {markov_result.baseline_accuracy:.1%}. "
        f"Training-only boundaries: Fast ≤ "
        f"{markov_result.medium_upper_seconds:.6f} s, Medium ≤ "
        f"{markov_result.slow_lower_seconds:.6f} s, otherwise Slow. "
        f"Training state observations: {state_counts}."
    )

    st.subheader("Transition Probability Matrix")
    show_left_aligned_table(
        markov_result.transition_probabilities.reset_index().round(4)
    )

    st.subheader("Held-out Prediction Outcomes")
    show_left_aligned_table(
        markov_result.confusion_matrix.reset_index()
    )
    st.caption(
        "Rows are actual run-10 states and columns are predicted states. "
        "Only consecutive passed timing observations are used; skipped and "
        "zero-duration records are excluded. Results are a one-step "
        "evaluation on the same collected suites, not evidence of "
        "cross-project generalization."
    )

    st.subheader("Sample Held-out Predictions")
    show_left_aligned_table(
        markov_result.predictions[
            [
                "node_id",
                "previous_state",
                "predicted_state",
                "actual_state",
                "correct",
            ]
        ].head(10)
    )
else:
    st.warning(
        "Raw timing observations for the Markov experiment were not found."
    )

# FOOTER

st.caption(
    "Experiments use saved project datasets and results. "
    "K-Means, linear regression, and the Markov model are supporting "
    "experiments; the core test-selection algorithms are evaluated separately."
)

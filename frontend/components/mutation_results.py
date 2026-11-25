import pandas as pd


def add_mutant_count_columns(sweep, total_mutants, detectable_mutants):
    if total_mutants < 0 or detectable_mutants < 0:
        raise ValueError("Mutant counts cannot be negative.")
    if detectable_mutants > total_mutants:
        raise ValueError("Detectable mutants cannot exceed sampled mutants.")
    if "mutants_caught_percentage" not in sweep.columns:
        raise ValueError("Budget sweep is missing mutants_caught_percentage.")

    result = sweep.copy()
    percentages = pd.to_numeric(
        result["mutants_caught_percentage"], errors="raise"
    )
    valid_percentages = percentages.notna()

    if (
        percentages[valid_percentages].lt(0).any()
        or percentages[valid_percentages].gt(100).any()
    ):
        raise ValueError("Mutant detection percentages must be between 0 and 100.")

    if detectable_mutants == 0:
        result["mutants_caught_count"] = float("nan")
        result["mutants_survived_count"] = float("nan")
        result["mutant_detection_percentage"] = float("nan")
        return result

    caught_estimate = percentages * detectable_mutants / 100
    caught_counts = caught_estimate.round()
    inconsistent = (
        valid_percentages
        & (caught_estimate - caught_counts).abs().gt(1e-6)
    )
    if inconsistent.any():
        raise ValueError(
            "Mutant detection percentages do not match integer kill-matrix counts."
        )

    caught_counts = caught_counts.where(valid_percentages)
    result["mutants_caught_count"] = caught_counts
    result["mutants_survived_count"] = (total_mutants - caught_counts).where(
        valid_percentages
    )
    result["mutant_detection_percentage"] = (
        caught_counts / total_mutants * 100
    ).where(valid_percentages)
    return result

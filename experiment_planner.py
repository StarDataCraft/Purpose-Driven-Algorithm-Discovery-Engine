"""Concrete minimal experiments tied to task, gap, and purpose constraints."""

from __future__ import annotations

from models import AlgorithmRecord, ExperimentPlan, GapSignature, PurposeContract


def build_experiment(purpose: PurposeContract, gap: GapSignature,
                     algorithm: AlgorithmRecord, candidate_label: str) -> ExperimentPlan:
    failure = gap.failure_type.casefold()
    if "drift" in failure:
        dataset, stressor = "SEA/Rotating Hyperplane plus an ordered real tabular stream", "recurring concept drift"
        extra = ["recovery time", "stationary-period accuracy", "false drift actions", "update latency"]
    elif "missing" in failure:
        dataset, stressor = "OpenML tabular dataset with controlled masks", "MCAR, MAR, MNAR and train-test missingness mismatch"
        extra = ["AUROC", "expected calibration error", "robustness curve"]
    elif "cluster" in purpose.task.casefold() or algorithm.family == "clustering":
        dataset, stressor = "anisotropic blobs and heterogeneous-density mixtures", "initialization and density variation"
        extra = ["ARI", "NMI", "cluster stability"]
    elif "regime" in failure:
        dataset, stressor = "synthetic switching process plus an ordered real series", "abrupt and recurring regime switches"
        extra = ["MAE", "post-shift recovery", "false regime alarm rate"]
    else:
        dataset, stressor = "task-appropriate public benchmark and controlled synthetic generator", gap.failure_type
        extra = ["robustness under stress", "stability across seeds"]
    metrics = list(dict.fromkeys([purpose.primary_metric, *purpose.secondary_metrics, *extra]))
    baselines = [
        algorithm.name,
        f"strong established {algorithm.family} baseline",
        "matched-compute baseline",
        "parameter-count-matched baseline",
    ]
    ablations = [
        "base algorithm only", "base + shuffled mechanism signal",
        "base + fixed non-adaptive mechanism", "full adaptive mechanism",
        "parameter-count-matched baseline", "simplified operator-only baseline",
    ]
    return ExperimentPlan(
        hypothesis=f"{candidate_label} improves {purpose.primary_metric} under {gap.failure_type} "
                   f"without degrading {', '.join(purpose.must_not_degrade) or 'normal-condition performance'}.",
        target_task=purpose.task, application_context=purpose.use_case,
        dataset=dataset, stressor=stressor, base_algorithm=algorithm.name,
        baselines=baselines, ablations=ablations, metrics=metrics,
        compute_reporting=["wall-clock time", "peak memory", "inference latency", "parameter count"],
        seeds=[11, 23, 47, 89, 131],
        success_rule=(
            f"pre-registered improvement in {purpose.primary_metric}; recovery time is the "
            "number of labeled observations required to return within the registered "
            "fraction of pre-drift performance, with no material protected-metric loss"
        ),
        failure_rule="confidence interval includes the minimum effect, or shuffled/fixed ablation matches the full method",
        information_audit={
            "training": purpose.available_training_information,
            "inference": purpose.available_inference_information,
            "forbidden": sorted(["future observations", "clean inference labels", "hidden ground-truth states"]),
        },
        expected_runtime_class="small-to-moderate bounded benchmark",
        reproducibility_notes="Freeze preprocessing, publish seeds/configuration, and report all runs including failures.",
    )

from evaluation.benchmark_tasks import load_benchmark_tasks
from evaluation.run_benchmark import run_offline_benchmark


def test_three_benchmarks_receive_complete_conservative_result_audits():
    reports = [
        run_offline_benchmark(task)
        for task in load_benchmark_tasks().values()
    ]
    assert all(report.result_audits for report in reports)
    for report in reports:
        for audit in report.result_audits:
            assert len(audit.audit_dimensions) == 10
            assert len(audit.robustness_results) == 10
            assert audit.final_decision.startswith("EXPLORATORY")
            assert audit.self_critique["strongest_reason_to_believe"]
            assert audit.self_critique["strongest_reason_to_reject"]
            assert any(
                item.name == "known_solution_novelty" and not item.passed
                for item in audit.audit_dimensions
            )

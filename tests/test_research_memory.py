from research_memory import ResearchMemory


def test_failures_persist_and_increase_penalty(tmp_path):
    path = tmp_path / "memory.db"
    memory = ResearchMemory(path)
    memory.remember_failure("fp", "duplicate of known method", "same structure")
    first = memory.failure_penalty("fp")
    memory.remember_failure("fp", "duplicate of known method", "repeated")
    assert memory.failure_penalty("fp") > first
    assert memory.failures()[0]["occurrences"] == 2
    memory.close()
    reopened = ResearchMemory(path)
    assert reopened.failure_penalty("fp") > 0
    reopened.close()


def test_structural_schema_migration_preserves_records(tmp_path):
    memory = ResearchMemory(tmp_path / "memory.db")
    memory.save("gap", "old", {"title": "existing"})
    memory.save_structural("coverage_gap", "new", {"title": "coverage"})
    assert memory.schema_version() == 3
    assert memory.list("gap")[0]["key"] == "old"
    memory.close()


def test_result_audits_are_append_only_and_comparable(tmp_path):
    from dataclasses import replace
    from evaluation.schemas import ResultAudit

    base = ResultAudit(
        audit_id="audit:one", run_id="run", direction_id="direction",
        gap_family_id="family", candidate_id="candidate",
        pipeline_version="pipeline-v1", commit_sha="abc",
        audit_timestamp="2026-08-01T00:00:00+00:00", task_name="task",
        search_mode="OFFLINE_FIXTURE", engine_mode="lightweight",
        audit_dimensions=[], detected_errors=[], severity_by_error={},
        supporting_evidence=[], recommended_repairs=[],
        state_of_art_candidates=[], experiments_run=[], adopted_changes=[],
        rejected_changes=[], before_metrics={}, after_metrics={},
        final_decision="EXPLORATORY",
    )
    memory = ResearchMemory(tmp_path / "memory.db")
    memory.save_result_audit(base)
    memory.save_result_audit(replace(
        base, audit_id="audit:two", pipeline_version="pipeline-v2",
    ))
    audits = memory.result_audits("candidate")
    assert len(audits) == 2
    assert {item["payload"]["pipeline_version"] for item in audits} == {
        "pipeline-v1", "pipeline-v2",
    }
    assert audits[0]["payload"]["audit_id"] in {"audit:one", "audit:two"}
    assert audits[0]["payload"]["candidate_id"] == "candidate"
    memory.close()

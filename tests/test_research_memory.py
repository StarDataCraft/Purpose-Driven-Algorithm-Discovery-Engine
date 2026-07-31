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
    assert memory.schema_version() == 2
    assert memory.list("gap")[0]["key"] == "old"
    memory.close()

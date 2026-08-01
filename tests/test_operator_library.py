from operator_library import OPERATOR_BY_ID, operator_is_compatible


def test_operator_compatibility():
    memory = OPERATOR_BY_ID["memory_retrieval"]
    assert operator_is_compatible(memory, "memory")
    assert not operator_is_compatible(memory, "objective")
    selection = OPERATOR_BY_ID["bounded_model_selection"]
    assert operator_is_compatible(selection, "model_selection")
    assert "verification window" in selection.formula_schema

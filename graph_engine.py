"""Bounded typed graph construction for traceable structural search."""

from __future__ import annotations

import networkx as nx

from models import AlgorithmRecord, GapSignature, MechanismSignature, Operator


def build_typed_graph(gaps: list[GapSignature], mechanisms: list[MechanismSignature],
                      algorithms: list[AlgorithmRecord], operators: list[Operator],
                      max_nodes: int = 1000) -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph()
    for gap in gaps:
        graph.add_node(gap.gap_id, kind="gap")
    for mechanism in mechanisms:
        graph.add_node(mechanism.mechanism_id, kind="mechanism", domain=mechanism.source_domain)
    for algorithm in algorithms:
        graph.add_node(algorithm.name, kind="algorithm", family=algorithm.family)
    for operator in operators:
        graph.add_node(operator.operator_id, kind="operator")
    for gap in gaps:
        for algorithm in algorithms:
            if gap.affected_algorithm in (algorithm.name, "Unspecified") or gap.affected_algorithm_family == algorithm.family:
                graph.add_edge(gap.gap_id, algorithm.name, relation="affects")
        for mechanism in mechanisms:
            if gap.affected_component in mechanism.compatible_slots:
                graph.add_edge(gap.gap_id, mechanism.mechanism_id, relation="structurally_aligns")
    for mechanism in mechanisms:
        for operator in operators:
            if set(mechanism.compatible_slots) & set(operator.compatible_slots):
                graph.add_edge(mechanism.mechanism_id, operator.operator_id, relation="realized_by")
    if graph.number_of_nodes() > max_nodes:
        raise ValueError(f"graph exceeds bound of {max_nodes} nodes")
    return graph

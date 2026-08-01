# Research Result explanation guide

Candidate changes are resolved from the delta field matching the affected component. Aggregation, routing, memory, objective, initialization, stopping, and component lifecycle are not incorrectly treated as update-rule changes.

Model-selection proposals follow the same rule. They must show candidate-score state, an observable trigger, and a bounded selection/verification rule rather than a generic “choose a better model” statement.

The Candidate Algorithms page starts with **Research Result / 研究结果**. It is
the primary interpretation layer; raw JSON is retained only in Technical
details.

The conclusion states the base algorithm, changed component, transferred
mechanism, intended failure boundary, and kill criterion. The derivation funnel
reports candidate papers → automatic relevance → evidence events → raw gap
instances → canonical families → promoted gaps → candidates. These counts are
different scopes and must not be substituted for one another.

Evidence is separated into **SUPPORTED** paper evidence, **SYSTEM-INFERRED**
deterministic derivation, and **UNKNOWN** missing evidence and validation. The
selected gap is copied into an immutable-shaped snapshot at selection time.

The primary presentation is now Part 3, **Explain the idea / 解释新想法**. It
adds deterministic evidence-flow, mechanism-transfer, before/after, and
experiment diagrams. Simplifying the presentation does not increase scientific
confidence.

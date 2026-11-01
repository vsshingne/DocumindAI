# Evaluation protocol (planned for Milestone 7)

No retrieval or generation benchmarks have been run in the foundation milestone.
There are no measured quality results to report yet.

The versioned synthetic dataset will contain document/page/chunk relevance labels,
questions, expected answers and expected abstention. Cases cover direct facts,
multi-page and cross-document reasoning, tables, ambiguity, contradictions and
questions with no supporting evidence. Fixture IDs must be mapped to the actual
ingested corpus rather than assumed to match generated IDs.

Retrieval metrics: Precision@K, Recall@K, MRR and nDCG@K with explicit relevance
units and treatment of duplicate hits. Generation metrics: citation validity,
citation precision/completeness, abstention accuracy and claim-level support.
Answer correctness and faithfulness require labeled or reviewed judgments; lexical
overlap alone will not be presented as semantic correctness. LLM judges, if added,
are supplementary with their model and prompt versions recorded.

Reports must include dataset hash/version, model identifiers/revisions, configuration,
hardware, run timestamp, per-case outputs, aggregate definitions and stage latencies.
Export JSON and CSV. Record unavailable metrics as null with a reason, not zero or
fabricated estimates. Resource and latency measurements must identify warm/cold
model state, concurrency and corpus size.

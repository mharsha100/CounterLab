# Paging case: source and implementation status

Primary specification: [Chen et al., arXiv v3](https://arxiv.org/html/2606.01342v3).
The reference uses its layer transitions (Eq. 3), candidate rule and RPB gate
(Algorithm 3). Gate state is read before the current request; its history value
is stored after a miss. Hits leave that history unchanged. This interpretation
is explicit in the protocol and remains subject to external implementation parity.

Priority lifecycle follows [OnlineMin, Section 3.1](https://cs.au.dk/~gerth/papers/tocs15.pdf):
priorities persist during support membership. We generate random relative ranks
by uniform insertion, removing ranks when a page leaves support.

`counterlab/learning_paging.py` is independently written. It uses exact layers
without forgiveness and simple data structures, so it does not claim the
published runtime or bounded-support implementation. Generated perfect/inverted
advice is supplied separately to the online pager and stored at each access.

The checker enumerates reachable caches/costs independently to verify layer
constraints. Perfect-advice comparisons and seeded event replays add finite
diagnostics; they do not verify the paper's asymptotic robustness claim.

Both report sources have now been retrieved using direct public HTTP requests.
Pinned versions and hashes are in [sources.json](sources.json); the inspected
contract differences are in [SOURCE_AUDIT.md](SOURCE_AUDIT.md). Gate-history
timing, priority refresh, prediction timing, and cost windows differ. A controlled
history-only diagnostic is implemented and passes with two controls. These
differences have not yet explained either report's overall result. The original
SPEC benchmark has not been reproduced, and G1 remains open. No third-party
implementation was copied or executed.

## New files

- `counterlab/learning_paging.py`: paper-linked reference state and eviction rules.
- `tests/test_learning_paging.py`: budget, gate, priority, replay, and input tests.
- `scripts/check_paper_reference.py`: independent finite verification and saved runs.
- This file: source locations, choices, and unresolved fidelity requirements.

Additional files from the source-comparison step:

- `sources.json`: pinned public source URLs, hashes, and inspected contract fields.
- `SOURCE_AUDIT.md`: the findings and the limits of the controlled diagnostic.
- `counterlab/protocol_variants.py`: changes only history timing in our own reference.
- `scripts/run_protocol_comparison.py`: verifies sources and runs the controlled diagnostic.
- `tests/test_protocol_comparison.py`: verifies that random draws/layers stay controlled.

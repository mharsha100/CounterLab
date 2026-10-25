# Paging source audit — October 21, 2026

## Selected original-scale supporting source slice — completed October 24

Protocol `30e56749a14d9b40c080b7a38267f9ef4cce75ff984b7912b0cf634f57fc080c`
was frozen before full numerical execution. The selection file predates fetching
the published numeric artifact. The selected dataset revision is
`0e2be0e71c25330eddbf452a0bd034ba1a3f6f24`, artifact `outputs/e4_robustness.json`.
Its Git blob and SHA-256 are pinned. No external algorithm code was executed.

The selected rows are uniform requests, k=16, n=150,000, inverted forecasts:
OnOPT-OM, RPB-OM(tau=1) and the source's LRU control. Algorithm seeds are 900–909;
request RNG seed is 66. The input is shared by all algorithm seeds. The initial
31-request prefix contains the first 16 distinct pages. Source layers and LRU
order reset to first-distinct order; stored forecasts use the last actual prefix
access. Priorities draw 16 initial values, then one per remaining request,
including hits: 149,985 draws per profile. The source's exact reset and RNG
schedule differ from our earlier cold-start common-tape lab study.

| Source row | Reported mean ratio | Reconstructed mean ratio | Mean/std residuals |
| --- | ---: | ---: | --- |
| OnOPT-OM | 4.325495426829268 | 4.325495426829268 | 0 / 0 |
| RPB-OM(tau=1) | 5.261394817073171 | 5.261394817073171 | 0 / 0 |
| Source LRU | 3.418064024390244 | 3.418064024390244 | 0 / 0 |

OPT after warmup is exactly 2,624 in all three rows. Ten randomized repeats and
one deterministic LRU run match the source's aggregation. The frozen tolerance
is exact OPT and absolute 1e-12 for both ratio mean and sample standard deviation.
These are selected aggregate matches, not proof of all runtime/implementation parity.

The preregistered intervention changes only RPB-OM(tau=1) history refresh from
every request to after a miss. Matched seeds add 247–285 misses (mean +259.5).
Source gate credits are zero; the after-miss arms earn 757–830 credits. This
identifies an operational timing effect in this source-linked finite regime.
The direction applies to these deliberately inverted forecasts and this trace;
it is not a general algorithm ranking or attribution of the entire disagreement.

Thirty profiles replayed twice in isolated Docker and once on host, with exact
event fingerprints. Independent prefix-optimal-state validation covers 530
profiles and 5,160 post-warmup events, including 30 original-input prefix checks.
It does not claim independent work-function enumeration over all full-length
events. The portable download reexecutes all 30 profiles and the prefix checker.
On-page verification checks the pinned record, raw published numeric artifact,
receipts and recomputed aggregates without repeating the full CPU experiment.

The official paper implementation, forgiveness, real SPEC traces, other source
regimes and the challenging lazy adversary remain open. Full research gate G1
and a theorem verdict are not marked complete. The run was developer-selected;
it is not evidence of new model experiment-selection ability.

The prior audit and development study below are historical foundations. Their
statements that no source regime was reproduced predate this selected slice.

## Latest gate review — October 24

The six pinned files passed the static contract checker again after the reporting
update. No downloaded implementation was executed. This does not complete
source fidelity or resolve the research disagreement.

| Required parity | Current evidence | Remaining work |
| --- | --- | --- |
| Our finite mathematical contract | Independent cache-state oracle matched 161,872 events | External implementation parity is separate |
| History/priority/prediction/window contracts | Six pinned inspections and controlled interventions | Match each source's complete combination and runtime semantics |
| Forecast/predictor generation | Shared lab forecast fields only | Reproduce an original predictor/corruption regime |
| Randomness and initial state | Paired common-input lab tape and empty starts | Match source draw schedule and resets |
| Request family and horizon | Finite uniform/cyclic tests and a constructed witness | Original regimes, lazy adversary where applicable, scale and repeats |
| Layer approximation/forgiveness | Exact-layer reference only | Establish use and behavior in each selected source regime |
| Full report disagreement | Finite mechanisms and plan/driver mismatch documented | Reproduce matched original regimes before attributing the overall disagreement |

Next scientific step: select one precisely documented original finite regime,
freeze its predictor, randomness, initialization, horizon and counting window,
then validate our independent implementation against that contract before
extending to the full reports. An asymptotic theorem is not assigned an
artificial finite experimental verdict.

The two report sources were retrieved successfully through direct public HTTP
requests after the web reader failed. Original files are kept in ignored
`downloads/source-audit/` for inspection only. No downloaded implementation was
imported, executed, or copied into CounterLab. Pinned URLs, content hashes, and
locators are in [sources.json](sources.json).

## Confirmed contract differences

| Choice | Supporting implementation | Challenging report's embedded implementation | Our reference |
| --- | --- | --- | --- |
| Gate history refresh | Every request | After a miss | After a miss |
| Random-priority refresh | Every request | Support entry | Support entry |
| Prediction scores | Stored at page access | Candidate scores supplied per step | Stored at page access |
| Miss-count window | After initial fill | Empty-cache start | Empty-cache start |

Supporting code is `simulate_om_family` at dataset revision
`0e2be0e71c25330eddbf452a0bd034ba1a3f6f24`; relevant assignments are lines 388
and 391. The challenge's embedded `_onopt`/`rpb_om` code is in the pinned
claim-1 page. The official repository's actual `access` implementation, revision
`7f0299c12ff1bdd02ba28f3f98a98c28ccbd8478`, updates gate history only when
the miss flag is set (lines 1569 and 1631). Read executed statements when
inspecting behavior; surrounding comments do not alone establish parity.

## Controlled development experiment

`scripts/run_protocol_comparison.py` changes only history timing in our own
reference. Its protocol is saved before execution. The constructed witness has
capacity 16, fixed predictions, seed 0 and tau 0. Priorities, request inputs,
initialization, and cost window are held fixed. It includes an all-pages-fit
control and a perfect-advice control, both checked against offline MIN.

Updating history after each request makes the next pre-request history equal to
the current number of unrevealed layers. Substituting that into the gate gives
`U <= (U + 2)/e - 2`, which cannot hold for nonnegative U. This is a deduction
about this timing rule. The recorded finite witness checks its operational effect.

This is a constructed development diagnostic, not a held-out evaluation. It does
not reproduce either entire report, attribute their overall disagreement to one
factor, rank the algorithms generally, or adjudicate the asymptotic theorem.
Original request families, prediction generation, scale and full implementation
parity still require investigation. Scientific gate G1 remains open.

## October 24: source contracts and finite factorial study

The follow-up checks six pinned files, including the supporting experiment
driver and challenging claim-2 report. Implementation text is parsed as syntax
trees; no external code is imported or executed. History and priority
assignments are checked inside their request/miss branches. Original numerical
reference files retain their earlier hashes.

The supporting protocol describes 200,000 requests and at least 20 repeats;
`e4_robustness` defaults to 150,000 and 10 in full mode. This discrepancy does
not identify which settings produced every published artifact. URLs, hashes
and locators are in [source_contracts.json](protocol_study/source_contracts.json).

### Committed method

[Protocol](protocol_study/protocol.json), SHA-256
`fda2101b9ce51e24d767eb6120a502495a8d38977c22ee89b5175af0e9306d37`,
was saved before observations. The original pre-execution plan binds this
protocol, source audit and worker image and is included in the portable bundle.

There are 52 development scenarios: capacities 4/8/16/32, uniform and cyclic
k+1-page families, perfect and time-varying noisy advice, three priority seeds,
three seed repeats of the known timing witness, and an all-fit control. Each has
all eight combinations of history timing, priority refresh and prediction
delivery. All 416 arms ran twice in Docker (832 executions), then passed host
replay. Every replay matched; inference requests were zero.

Within a matched pair, inputs, forecast field, priority tape, initial cache,
tau, layer/candidate rules and ties stay fixed. The tape isolates interventions;
it is not the sources' original seeded schedule. The shared prefix has k
distinct pages and the finite tails have 256 requests. The source experiment
scale and the challenge's lazy adversary are not reproduced. Exact layers omit
forgiveness. Forecasts are lab data, not learned models or the source predictors.

### Complete results

| Changed setting (level 0 → level 1) | Matched pairs | Different misses | Different gate credits | Signed miss delta range |
| --- | ---: | ---: | ---: | ---: |
| History: after miss → every request | 208 | 25 | 69 | −2 to +5 |
| Priorities: entry → every request | 208 | 75 | 11 | −5 to +6 |
| Predictions: at access → at decision | 208 | 98 | 28 | −8 to +12 |

Deltas are level 1 minus level 0. Both signs occur; no setting universally
improves miss counts in this suite. All matched edges, including null results,
are retained. Arms and seed repeats are correlated, not independent scientific
cases. This is development reuse, not held-out agent evaluation.

Changing only the counting window changes 212 defined ratios without changing
an eviction. All-fit post-warmup ratios stay undefined (0/0). Both ALG and
offline MIN use the same window.

All four preregistered controls pass: after-request history earns no credits;
perfect advice matches MIN; no arm beats MIN; all-fit post-warmup cost is zero
with undefined ratios. Before freezing, an independent exhaustive oracle
checked perfect-advice optimality on 140 tiny traces across eight arms (1,120
comparisons).

The known witness's first different gate decision is request 29: U=4 and Y=15
give threshold 4.254 and a credit; Y=4 gives threshold 0.207 and no credit. See
[witness.json](protocol_study/witness.json) for the event and trace fingerprints.

### Supported conclusion and remaining gates

The inspected contract choices can independently change finite measurements.
This quantifies mechanisms that a static source diff cannot quantify. It does
not explain the reports' entire disagreement, establish external implementation
parity, reproduce their figures, adjudicate the theorem, or complete G1/G2/G3.
A finite trend across a few cache sizes cannot establish or refute an O(1) term.

No license declaration was found in the cached official repository metadata or
tree at the inspected revision. External implementation redistribution remains
unestablished; exports contain only our own code, facts and source references.

The app's **Research study** screen exposes all arms, conditional maps, cost
windows, controls and the complete standalone numerical replay. Hash and
numerical verification precede display. Replay needs only Python 3.13.

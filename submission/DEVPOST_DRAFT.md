# CounterLab

**Tagline:** Turn research disagreement into experiments you can replay.

**Proposed track:** Best Apps and Agents.

## The problem

When two algorithm implementations produce different results, an explanation
alone is not enough. A useful investigator must choose a test that separates
the explanations, commit what it expects, run the test and preserve the evidence
even when its prediction fails.

## What we built

CounterLab is an experimental investigation workspace for one reviewed
learning-augmented paging case. It connects NVIDIA Nemotron through Nebius Token
Factory to a bounded experiment workflow. Nemotron proposes a test and commits
predictions about gate behavior and cache misses. Contract checks reject invalid
interventions. Restricted local Docker workers run admitted tests twice; host
replay checks the measurements. A deterministic factual report cites all measured
tests and distinguishes controls, rejections, null results and unresolved claims.

A claim audit connects five developer-framed questions to exact verified record
fields, comparability checks and unresolved coverage. It does not autonomously
extract claims or resolve the full research disagreement.

The React/TypeScript interface exposes source contracts, predictions, measurements,
failures, model usage and downloadable standard-library Python replays. A keyless
evidence build lets a judge inspect saved results without creating a paid account.
It is labeled as recorded inspection; the full source build contains live inference.

A separate human-designed workbench exposes bounded synthetic settings and
precommitted expectations. Its local calculator and checked standard-library
Python runner enable new comparisons without an inference key. Those results
remain explicitly separate from the frozen model scores.

## How Nebius and NVIDIA are used

The Python backend sends runtime inference requests to **Nebius Token Factory**
using **`nvidia/Nemotron-3-Ultra-550b-a55b`**. Nemotron selects experiments and
precommits predictions. It does not invent the measured counts or write the final
factual report. Local Docker provides numerical execution; Nebius AI Cloud,
Serverless Jobs/Endpoints/DevPods and Tavily are not used in this implementation.

## What the evidence shows

In the latest frozen source evaluation, eight tasks compared two Nemotron
planning policies with two zero-inference baselines. The model batch used 27
calls, 101,300 reported tokens and no retries. Independent full-trace validation
checked 45 distinct profiles and 145,041 post-warmup events.

| Policy | Available finite differences found | Both predictions correct | Model calls |
| --- | ---: | ---: | ---: |
| Nemotron adaptive | 2 / 2 | 2 / 11 | 13 |
| Nemotron fixed choices | 1 / 2 | 1 / 10 | 14 |
| Contract heuristic | 2 / 2 | 9 / 12 | 0 |
| Seeded random | 2 / 2 | 8 / 11 | 0 |

These are correlated development diagnostics with one synthetic generator,
adapter and repeat, not a general model ranking. No selection advantage over the
heuristic is established. Truncated responses and wrong predictions remain in
the evidence. Factual report integrity is a backend check, not a reasoning score.

A later retrospective input-only audit identified contradictory predictions.
The latest workflow now rejects those contradictions before execution and can
feed the reason back for another proposal. That workflow is verified with
simulated planning and real numerical execution; live model improvement remains
unmeasured. Prior evaluation records and scores are unchanged.

## What is distinctive

The product makes a failed prediction inspectable. Plans are saved before
execution; admission and prediction checks are saved before the worker starts;
the final factual report is derived from measurements. The download lets another
person recompute the finite result without trusting a screenshot, buying tokens
or rerunning a model. The baseline comparison also tests whether AI selection
adds value rather than assuming that it does.

## Limits and next steps

The source investigator supports fixed reviewed tests, with a separate bounded
synthetic adapter for human experimentation. Neither accepts arbitrary papers or code for
execution. It independently reconstructed one selected supporting reproduction
slice; it has not reproduced the paper's full experiments or resolved the full
report disagreement or an asymptotic theorem. External user validation and a
broader independent benchmark remain future work.

## Built with

Nebius Token Factory; NVIDIA Nemotron; Python; FastAPI; SQLite; Docker;
React; TypeScript; Vite. Solo entrant, AI-assisted development.

## Links to complete before submitting

- Public working demo or test-build URL: **pending publication and verification**.
- Public source repository: **pending publication**.
- Public demo video (target 2:55): **private rehearsal cut prepared; final recording and public upload pending**.
- Tool feedback: use `TOOL_FEEDBACK.md`.

This is a draft, not a completed Devpost submission. Review ownership,
third-party notices and the access checklist before publishing. New builds omit
the full upstream reference; the optional source replay setup retrieves and
hash-checks it only when explicitly requested.

# CounterLab

**Tagline:** Turn research disagreement into experiments you can replay.

**Track:** Best Apps and Agents.

The sections below follow Devpost's project-story fields so they can be pasted
in order. Replace the pending links at the end before submitting.

## Inspiration

In [Hugging Face's open reproduction effort for ICML 2026](https://huggingface.co/blog/icml-2026-open-reproductions), independent teams
reached opposite verdicts on the same claims for 242 papers. When a result does
not reproduce, or two implementations of "the same" method disagree, asking an
AI *why* produces a fluent explanation, but an explanation is not evidence. We
wanted an AI investigator that has to earn its conclusions: choose a test that
separates the explanations, commit to a prediction first, run it safely, and
leave behind evidence anyone can recompute.

## What it does

You upload a paper (PDF, Markdown, LaTeX or text, or an arXiv/OpenReview link),
the code behind it (Python files, a ZIP, or a GitHub link), or two
implementations that disagree, and type the question you want settled.

1. **NVIDIA Nemotron 3 Ultra on Nebius Token Factory** reads the inputs as data,
   picks a claim it can test, names two to four competing explanations and the
   outcome each one expects, commits a bet, and writes the experiment harness,
   all as one strict-schema JSON response, before anything runs.
2. A **deterministic guard** rejects designs whose explanations expect the same
   outcome, and harnesses that ignore the uploaded code, use the network or
   processes, or ignore the seed. Nemotron gets one redesign per experiment before commitment
   and bounded harness repairs with its predictions locked (up to two for the first experiment,
   one for the follow-up), within the overall planning-turn cap.
3. The uploaded code runs in a **sealed Docker sandbox** (no network, read-only,
   non-root, resource limits, no credentials). CounterLab, not the harness, runs
   every condition on the same seeds, then repeats the whole run; values must
   match exactly.
4. **Code writes the finding** from the measurements: means and spread, which
   expectations held, a sign test, which explanations survive, and whether
   Nemotron's bet held. The model never writes a number in the report.
5. Nemotron designs **one follow-up experiment** from CounterLab's measured
   summary, and the whole investigation downloads as a sealed package. Standard-library Python
   verifies its hashes and recomputes findings from saved measurements. An optional
   rerun executes the included code locally and needs its dependencies.

It works like a product, not a results page: a home dashboard, one form to start an
investigation, a live investigation page with a progress rail (stop it at any time, or run it
again on the same inputs), a searchable list of sealed investigations, and Settings where you
paste your Nebius key, check that Nemotron is available, send a test request and build the
sandbox, all from the browser. Temporary Nebius errors are retried automatically and recorded.

Three bundled examples are ready to investigate: two reservoir samplers that disagree, a
paper-only claim about Welford's variance algorithm (both methods implemented
from the text), and a cache-eviction disagreement between the authors' code and
a reproduction that differ only in when predictions are refreshed.

The first live run (October 30, Nemotron 3 Ultra, 87 seconds, three model calls)
took the cache example. Nemotron bet that refreshing only on misses causes fewer
misses; the measurements contradicted it (601.9 vs 557.3 misses, 0 of 10 seeds
agreeing). Its follow-up harness then crashed in the sandbox on all 40
measurements. CounterLab returned the traceback, Nemotron repaired the harness in
four seconds, and the repaired experiment showed refreshing on every request
stays ahead with perfect and with noisy predictions (10 of 10 seeds each). Its
follow-up bet held.

CounterLab also includes a deep **case study** of a real published disagreement
in learning-augmented paging (ICML 2026), with a frozen evaluation of Nemotron
against zero-inference baselines, independent full-trace validation and eight
replay packages.

## How we built it

- **Backend:** Python 3.13, FastAPI, SQLite and pypdf. Token Factory's
  OpenAI-compatible `chat/completions` with `nvidia/Nemotron-3-Ultra-550b-a55b`,
  `response_format: json_schema` with `strict: true`, temperature 1.0 and top_p
  0.95, a 15-minute timeout for reasoning plus
  code generation and at most seven model turns per investigation. Temporary
  errors (connection drops, timeouts, 429, 5xx) are retried with backoff that
  honours `Retry-After`, the way the OpenAI SDK does; if the strict schema is
  rejected the request falls back to a relaxed schema and then JSON mode, and
  every retry and fallback is recorded. The model must be in the account
  catalog (the strongest available Nemotron is used otherwise) and must match
  the returned model.
- **Sandbox:** a pinned Python 3.13 image with numpy, scipy, pandas,
  scikit-learn and networkx; `--network=none`, `--read-only`, `--cap-drop=ALL`,
  `no-new-privileges`, CPU/memory/process/time limits, inputs on stdin, no host
  mounts. A boundary probe verifies all of this after every build.
- **Integrity:** every plan is hashed and saved before execution; every run is
  sealed with a SHA-256 manifest; verification recomputes every finding from the
  saved sandbox rows and rejects edited evidence.
- **Frontend:** React 19, TypeScript and Vite, built to Vercel's Web Interface
  Guidelines: keyboard operation and a command palette, deep-linked state,
  validation beside fields, loading, empty and error states, confirmation for
  destructive actions, self-hosted IBM Plex. A static evidence edition serves
  verified snapshots with no backend for hosted judging.
- **Quality:** The documented pre-live-run milestone passed 292 offline Python tests (including a local fake Token Factory
  that injects 429s, 503s, dropped connections, timeouts and schema rejections,
  and real Docker sandbox checks), 25 frontend tests, a browser walkthrough of
  the whole product flow and both editions, and an axe-core scan using WCAG A/AA rules across
  23 views and tabs with no reported violations. This is not a complete accessibility certification;
  subsequent live-run fixes and validation are recorded in `submission/VALIDATION.md`.

## Challenges we ran into

- **Is the AI actually helping?** In the case study we measured it instead of
  assuming it: adaptive Nemotron found both available differences (2/2), but so
  did a zero-inference heuristic, and its two predictions were both right in
  only 2 of 11 measured tests. That is why every open investigation scores the
  bet and keeps failed predictions on the record.
- **Running anyone's code safely.** Uploaded code and model-written harnesses
  are untrusted. They run only in a container with no network or credentials,
  and the runner, not the harness, controls the loop, so conditions stay paired.
- **Model output that doesn't fit.** Designs that cannot tell explanations apart,
  harnesses with wrong file paths, truncated responses: each has a bounded,
  logged recovery path instead of a silent retry.

## Accomplishments that we're proud of

- Supported papers and code can go from a question to a committed, bounded, repeated
  experiment in one flow, with the model's role and failures visible at every step.
- The first live run shows the loop working as designed: Nemotron's bet failed
  and the report says so; its broken follow-up harness was caught in the sandbox,
  repaired from the traceback, and measured, all in 87 seconds.
- In the case study, three selected aggregates from the supporting report
  (k=16, 150,000 requests, ten seeds) reproduce exactly, and an independent
  full-trace oracle checked 45 profiles and 145,041 post-warmup events.

## What we learned

A capable model is a good experiment designer and an unreliable predictor. The
useful design is to let Nemotron propose and bet, and to let deterministic
checks, isolation and repeated measurement decide what counts as evidence.

## What's next

- A frozen benchmark of open investigations on contested ICML 2026 claims,
  scored against simple baselines like the case study.
- Running the sandbox on Nebius AI Cloud Serverless Jobs so anyone can use the
  live workflow from a hosted page, and GPU-backed experiments.
- Multi-language sandboxes, so non-Python code no longer needs a port.

## Limits

Open investigations run Python on CPU under a 240-second limit per sandbox run; other languages are
re-implemented and labelled. An experiment tests the uploaded code under
Nemotron's harness and settings, so reviewing the harness is part of reading the
result. One open investigation has run live with Nemotron and is recorded; the
other recorded open examples use simulated planning (labelled). One live run
shows the workflow works; open design quality has not yet been benchmarked. The hosted edition shows recorded
investigations and makes no model calls; the live workflow runs from the source
build with your key.

## How Nebius and NVIDIA are used (for the sponsor-tools field)

The Python backend sends runtime inference requests to **Nebius Token Factory**
using **NVIDIA Nemotron 3 Ultra** (`nvidia/Nemotron-3-Ultra-550b-a55b`).
Nemotron reads the uploads, designs and commits experiments, writes and repairs
the harness code, and designs follow-ups; it does not produce measurements or
the factual report. Uploaded code runs in local Docker; Nebius AI Cloud compute
and Tavily are not used. Detailed tool feedback: `TOOL_FEEDBACK.md`.

## Built with

nebius-token-factory, nvidia-nemotron, python, fastapi, pydantic, sqlite, pypdf,
docker, react, typescript, vite. Solo entrant; AI-assisted development.

## Links to complete before submitting

- Public working demo or test-build URL: **pending publication and verification**.
- Source repository: https://github.com/mharsha100/CounterLab (**private; make
  public and verify before submitting**).
- Public demo video, under three minutes: **pending recording and upload**.

This is a draft, not a completed Devpost submission. Review ownership,
third-party notices and the access checklist before publishing.

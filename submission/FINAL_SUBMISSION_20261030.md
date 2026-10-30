# CounterLab — final submission copy, October 30

Prepared from the current Open Lab implementation and recorded evidence. This
file is not a submission receipt. Use the story below for the current product;
the October 26 one-adapter description and rehearsal video are historical.

## Entry fields

- **Name:** CounterLab
- **Tagline:** Turn research disagreement into experiments you can replay.
- **Track:** Best Apps and Agents
- **Built with:** Nebius Token Factory, NVIDIA Nemotron, Python, FastAPI,
  Pydantic, SQLite, pypdf, Docker, React, TypeScript, Vite.
- **Team:** Solo entrant; AI-assisted development.

## Project story — ready to paste

### Inspiration

When two implementations disagree, another fluent explanation is not enough.
Researchers need a test that separates the explanations, a prediction made
before execution, and evidence someone else can check. Hugging Face's ICML 2026
reproduction effort reported 242 papers with opposing reproduction verdicts on
the same claims. That motivated CounterLab: an AI investigator whose bets can
fail in public, without its findings being rewritten to hide the failure.
[Source](https://huggingface.co/blog/icml-2026-open-reproductions).

### What it does

Upload a supported paper or code, supply a repository or paper link, or start
with a bundled example. Ask the question you want tested. **NVIDIA Nemotron 3
Ultra on Nebius Token Factory** reads the inputs, chooses a testable claim,
names competing explanations and their expected outcomes, commits its bet and
writes the experiment harness.

CounterLab checks the design before running it. Uploaded code and the generated
harness execute in a restricted local Docker container with no network or
credentials. The same conditions and seeds run twice. Only matching, validated
measurements become evidence. Deterministic code computes the finding, including
which expectations held, failed or remained inconclusive. Nemotron can propose
one follow-up and repair a failing harness within fixed limits while the
committed predictions stay unchanged.

The interface includes setup checks, an investigation form, progress and Stop
controls, per-experiment charts and verdicts, searchable history, model activity,
and a downloadable record. Its default Python replay checks file hashes and
recomputes findings from saved measurements without an API key. Optional
re-execution runs the included code locally and needs that code's dependencies.

### A real run, including the failure

Our recorded October 30 live investigation used Nemotron 3 Ultra through Nebius
Token Factory and completed in 87 seconds: three model calls, 23,005 reported
tokens and no transport retries. On the bundled cache example, Nemotron's first
bet failed. Refreshing predictions only on misses averaged 601.9 misses;
refreshing on every request averaged 557.3. None of ten seeds supported its bet.

The follow-up harness initially crashed on all 40 measurements. CounterLab
returned the traceback; Nemotron repaired the harness. The repaired experiment
matched its repeat execution and its follow-up bet held on ten of ten seeds
for both comparisons. The unsuccessful bet and broken attempt remain visible.

Three other recorded open examples use clearly labelled simulated planning
with real numerical execution. They test the integration and are not evidence
of Nemotron's design quality.

### How we built it

Python/FastAPI coordinates intake, schema-checked Nemotron responses, admission,
bounded Docker execution and record sealing. React/TypeScript presents every
committed plan, result and failure. Token Factory supplies runtime inference;
Nemotron performs design, code generation, repair and follow-up. The measurement
loop and factual reporting stay in deterministic code. Transient provider errors
have bounded, recorded retries; redesign and harness repair are separate,
limited planning turns. The hosted edition exposes recorded investigations;
the full source build runs new investigations locally.

### What we learned

We also built a deep learning-augmented paging case study with a frozen
eight-task comparison against non-AI baselines. Adaptive Nemotron found both
available finite differences, but so did a simple heuristic; its two predictions
were both correct on only 2 of 11 measured tests. We have not established an AI
selection advantage. That is why the product preserves predictions, controls,
failed attempts and independently checkable measurements instead of presenting
a confident model-written conclusion.

### Limits and next steps

Open Lab supports bounded Python/CPU experiments. Scanned PDFs, large training
runs and arbitrary services are outside its current scope. Other languages may
be read and reimplemented in Python, with that limitation recorded. Generated
harnesses still require scientific review: repeated output does not prove that
an experiment measures the intended claim. One live open run demonstrates the
workflow, not general reliability or a benchmark advantage. The paging case
study does not settle the full published disagreement or theorem.

Next are a frozen benchmark of open investigations, more language runtimes and
hosted execution. Nebius AI Cloud and Tavily are not used in the current build.

## Required sponsor feedback — ready to paste

**Nebius Token Factory.** We used its OpenAI-compatible API to run NVIDIA
Nemotron for experiment design, structured predictions, harness generation,
repair and follow-up. In the October 30 live run, all three model calls accepted
the strict JSON schema, returned the requested Ultra model and needed no
transport retry or schema fallback. Saved token usage, finish reasons and model
IDs made the run auditable. Onboarding involved account setup, a promotional
form and emailed redemption code, backend credentials, model discovery and
text/structured-output probes; the Builders Program credit arrived separately.
We did not measure an exact onboarding duration. Clearer per-model guidance on
reasoning/output allowances and failure handling would help: earlier Super-VL
probes exhausted 4,096 and 8,192 output tokens before a usable plan. We would use
Token Factory again for hosted open-model experiments with explicit budgets and
recorded failures.

**NVIDIA Nemotron.** We used `nvidia/Nemotron-3-Ultra-550b-a55b` as the experiment
designer and code author. It generated two designs and repaired its own failing
follow-up harness from the traceback in our live run. Its first prediction was
wrong; the repaired follow-up bet held. In the earlier paging evaluation,
prediction accuracy was weak and a zero-inference heuristic found the same two
differences. We accessed the model through Nebius, without installing weights
locally. We would use it again as a proposer whose outputs are validated and
measured, not as an autonomous authority on scientific truth. Broader design
quality remains unmeasured.

**Other services.** Numerical execution uses local Docker. We did not use
Nebius AI Cloud compute, Tavily or other partner services, and claim no user
experience with those services. Longer observed feedback is in TOOL_FEEDBACK.md.

## Judge instructions — ready after actual build URL is inserted

The hosted edition is recorded evidence and makes no model calls. Open Home,
then Investigations and the October 30 live Nemotron cache investigation. Inspect
Experiment 1's failed bet, Experiment 2's failed harness and repair, the measured
verdicts, Activity and the record. Keep its live-model label distinct from the
three simulated-planning examples.

Download its replay package, extract it and run `python replay.py`. This checks
hashes and recomputes findings from stored measurements; it does not regenerate
model replies. Optional `--rerun` executes the included code on your machine,
requires its imported packages and does not itself provide Docker isolation.

Use **Case study → Evaluation** for the four-policy benchmark, and **Case study
→ Evidence** for the separate paging replay packages. For portable inspection,
extract the complete judge ZIP, run `python serve.py`, and open the printed
localhost URL. No model key or Docker is required for recorded inspection.
The full source README explains new local investigations with Python 3.13,
Docker Desktop and a Nebius Token Factory key.

## Links and final gates — do not paste unresolved items into Devpost

| Item | Current known destination / remaining check |
| --- | --- |
| Source | https://github.com/mharsha100/CounterLab — verify final commit, public visibility and visible MIT license after the authorized publication step |
| Working demo or test build | Insert the actual deployed URL or publicly downloadable functioning build, then verify access |
| Video | Insert the actual publicly visible YouTube URL; no final uploaded functioning-app video was verified while preparing this file |
| Submission | Record the actual Devpost entry and confirmation after submission |

The [official rules](https://nebiusglobalaihackathon.devpost.com/rules), checked
October 30, require a public licensed source repository, a working demo/hosted
app/test-build link, English materials, sponsor feedback and a publicly visible
YouTube demonstration showing the functioning project. Keep the video below
three minutes. Submission closes **October 30 at 10:00 AM Pacific / 1:00 PM
Eastern**. The updated judging period is **December 9–23**, so maintain free
unrestricted judge access through **December 23 at noon Pacific**.

## Current video script — recorded live-run walkthrough, target 150–165 seconds

Keep an on-screen label: **Recorded live Nemotron investigation · October 30**.
Capture actual navigation and replay verification. Do not present saved results
as fresh inference or replay a simulated record under a live-model label.

| Time | Screen | Narration |
| --- | --- | --- |
| 0:00–0:15 | Home | When two implementations disagree, a fluent explanation is not enough. CounterLab helps researchers turn that disagreement into an experiment with a prediction, a measurement, and evidence they can check. |
| 0:15–0:35 | New investigation / bundled cache example | Bring a supported paper or code, and ask your question. NVIDIA Nemotron 3 Ultra, running on Nebius Token Factory, reads the inputs, names competing explanations, commits a bet, and writes the experiment harness. This walkthrough opens a saved live run; it does not make new model calls. |
| 0:35–0:55 | Experiment 1 committed plan | The plan is saved before execution. A deterministic guard checks the design, then the code runs twice in a restricted Docker container, without network access or credentials. Both runs use the same seeds. |
| 0:55–1:25 | Experiment 1 results and bet | Here Nemotron predicted that refreshing cache predictions only after a miss would cause fewer misses. The measurements contradicted it: six hundred one point nine misses, compared with five hundred fifty-seven point three when refreshed every request. None of the ten seeds supported its bet. CounterLab keeps that failure visible. The finding is computed from measurements, not written by the model. |
| 1:25–1:52 | Experiment 2 checks and repair | Nemotron then designed a follow-up. Its first harness crashed. CounterLab returned the traceback; Nemotron repaired the code while the committed predictions stayed fixed. The repaired experiment repeated exactly, and its follow-up bet held on ten out of ten seeds. |
| 1:52–2:20 | Record download / actual replay, brief case-study table | Download the sealed record and run the included Python replay. It verifies the files and recomputes findings from saved measurements, without an API key. The separate paging case study also compares Nemotron with simple baselines. We show that the heuristic found both differences too. |
| 2:20–2:40 | Closing product view | This live investigation completed in eighty-seven seconds with three model calls. It demonstrates the workflow, not general scientific reliability. CounterLab: committed predictions, preserved failures, and evidence you can replay, powered by Nebius Token Factory and NVIDIA Nemotron. |

Timing is a recording plan, not a verified encoded duration. Verify the finished
file and YouTube playback. The earlier October 26 edited-still cut is not the
final video for the current Open Lab product.

## Evidence checked while preparing this copy

- Current README and the intake, planner, guard, workflow, sandbox, reporting
  and record-export implementation under `counterlab/open_lab/`.
- Live run `cases/open_lab/recorded/f37f1506613e4c78b194a93265caa0e7/summary.json`:
  exact model ID, three model calls, 23,005 reported tokens, 87 seconds, strict
  response format and zero retries. `provider_requests` is four; do not describe
  this as three total HTTP requests.
- `submission/VALIDATION.md` for the measured counts and retained failed repair
  attempt. Other recorded examples are not counted as live Nemotron evidence.
- No new provider calls, tests or browser actions were made to prepare this copy.

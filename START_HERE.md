# Hackathon project planning package

**Updated October 28, 2026 (product UI).** CounterLab now looks and works like a product: Home,
New investigation, Investigations, a live investigation page (Stop, Run again, replay package) and
Settings, where you paste your Nebius key, check the connection, send a test request and build the
sandbox from the browser. Temporary Nebius errors are retried automatically and recorded. To use it:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt   # required: adds pypdf
.\.venv\Scripts\python.exe scripts\start_app.py                      # opens the browser
```

Then Settings → save the key → Check connection → Send a test request → Set up sandbox, and New
investigation. Details: README → Quick start, The app, Reliability of the Nemotron connection;
`submission/VALIDATION.md → Product interface and connection hardening`.

**Updated October 27, 2026 (open investigations).** CounterLab now investigates
**any uploaded paper or code**: the first screen, **New investigation**, takes a
paper, code, two disagreeing implementations or links, and runs Nemotron design
and commitment → guard → Docker sandbox (run twice) → code-written report →
follow-up → sealed replay package. To use it live:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt   # required: adds pypdf
.\.venv\Scripts\python.exe scripts\setup_open_runner.py               # once, Docker Desktop running
.\.venv\Scripts\python.exe scripts\start_app.py
```

**October 30:** the first live Nemotron open investigation ran end to end on the
entrant's machine (Nemotron 3 Ultra, 3 requests, 23,005 tokens, 87 s, no retries,
including a sandbox crash that Nemotron repaired from the traceback). It is promoted
into the recorded examples (`cases/open_lab/recorded/f37f1506613e4c78b194a93265caa0e7`)
and gallery images 01 and 03–07 were recaptured from it. The other three recorded
examples remain labelled simulated planning. Details: README → What an investigation does, APP_GUIDE →
Investigate any paper or code, `submission/VALIDATION.md → Open investigations`.

**Earlier on October 27:** Final submission polish is verified; see
`submission/VALIDATION.md → Final submission polish` and `submission/SUBMISSION_PACKET.md`
for the gallery images, Devpost copy and recommended video plan. Earlier
idea-comparison and preparation documents now live in `docs/planning/`.

Start with **README → Quick start**, then
`PROJECT_COUNTDOWN.md` for the remaining work and `submission/PROJECT_FREEZE.md`
for the reviewed release scope. Those documents supersede the historical setup
and progress notes below. Publication, judge access, final video and submission
are separate deliverables; the repository remains private.

**Previous publication-preparation milestone:** New packages omit the full upstream
numeric file and include an explicit hash-verified reference setup. The evidence
interface links its full source build. A manual-only GitHub Pages workflow and
finished narration draft are prepared locally. Start with
`submission/PUBLICATION_GUIDE.md`. Repository destination, actual public deployment
and video recording remain pending; no new inference or cash spending.

**Previous delivery milestone:** A separate keyless evidence build and full source
release are prepared locally, with downloadable replays, package integrity checks
and submission drafts. Start with **DEVELOPMENT_LOG → Portable evidence release** and
`submission/JUDGE_GUIDE.md`. No new inference, account setup or Docker is needed
to inspect the extracted evidence build. Public links/video and upstream numeric
artifact redistribution review remain pending.

**Previous implementation milestone:** **Research study → Source investigator** now starts the
separately versioned v2 workflow. It commits the prediction, checks necessary
conditions before worker execution and uses rejection feedback for an untried
follow-up. Rejections supply no measured counts. The saved v2 example uses
simulated planning and two real isolated numerical replays; it is not a new
Nemotron evaluation. All frozen v1 records and benchmark scores remain intact.

```powershell
.\.venv\Scripts\python.exe scripts\start_app.py --read-only --port 8001
```

Open **http://127.0.0.1:8001/?view=source-investigator**. Inspection needs no API
key or Docker. The new example opens first; the earlier source example remains
in the selector. All investigation starts are blocked in this mode. See
**APP_GUIDE → Guarded source workflow** for the new files and replay.

**Verified:** 162 offline tests, production build, real worker boundary probe,
two isolated numerical replays and actual HTTP download/fresh-process replay.
Zero new model calls: cumulative reported usage stays 413,410 tokens / 79 calls.
V2 model quality is unmeasured; no model advantage is claimed. External judge
access, broader source fidelity and final submission assets remain open.

The implementation/preparation entries below are earlier milestones.

**Latest implementation milestone:** **Research study → Source investigator**
connects the validated source regime to bounded planning. The saved example uses
simulated plans and four actual Docker executions: repeat control → matched
history intervention → complete factual report → credit-free standalone replay.
It is available for inspection immediately and is not a Nemotron performance
claim. New live runs require separate source-view credit consent. All 107 tests
and the build pass. Eight fresh evaluation tasks are frozen but unrun; their
isolated evaluation environment still needs preparation. No new credits used.

The source reconstruction and reporting entries below describe earlier milestones.

**Latest scientific milestone:** **Research study → Source reproduction** now
shows an original-scale supporting-report E4 slice: k=16, 150,000 requests,
inverted forecasts and ten algorithm seeds. All three selected published
OPT/mean/std aggregates match. Changing only history refresh adds 247–285 misses
across all ten paired seeds. Thirty profiles matched across two isolated replays
and a host replay; the portable full replay also passes. All 92 tests and the
build pass. This is one source-linked finite reconstruction, selected by the
developer; full report fidelity and model planning advantage remain open.
No new live model calls or credits were used.

**Latest milestone:** New investigations use at most two Nemotron planning calls
and no final reporting call. Factual reports use every replayed measurement,
retaining nulls and all citations. Older model answers and frozen evaluation
scores remain unchanged. All 92 tests, the build, real Docker paths with
simulated planning and portable report replay pass. No new live inference was
used. Restart the app and inspect the finding at the end of **Investigation**.
Source fidelity, live validation of this changed workflow and judging access
remain open.

## Recommendation

**CounterLab — turn disagreement into experiments.**

The ambitious recommendation is an AI investigator that compares conflicting computational research claims, proposes a discriminating experiment, executes a controlled test, and produces a conditional, reproducible finding. NVIDIA Nemotron runs through Nebius Token Factory. Recommended track: **Best Apps and Agents**. Real experiment adapters and agent value are unproven first-build gates.

## Read in this order

**Current state:** The local app, isolated Docker worker, source study, independent mathematical validation and frozen agent benchmark are implemented. Follow [APP_GUIDE](APP_GUIDE.md): run `.\.venv\Scripts\python.exe scripts\start_app.py`, then visit http://127.0.0.1:8000. Restart an existing server and open **Evaluation**. Inspection and portable replay use no credits. All 92 offline tests and the production build pass. Keep Docker Desktop running for new investigations. Earlier research plans remain preserved below.

**Research and evaluation update:** The six-source study covers 52 scenarios, 416 profiles and 624 matched comparisons. Independent mathematical checking matched 161,872 events. The approved eight-task model benchmark used 36/40 calls and 240,279 reported tokens. Adaptive found 2/2 available differences, fixed plan 1/2; both simple baselines found 2/2. Only 3/8 adaptive and 1/8 fixed-plan findings passed all evidence/scope checks. No advantage over simple selection policies is established; autonomous reporting targets are unmet. Failures remain visible alongside checked interpretations. Full external implementation parity, G1 and judging deployment remain open. See [README](README.md) and [source audit](cases/paging/SOURCE_AUDIT.md).

1. [Ambitious idea comparison](docs/planning/AMBITIOUS_IDEA_COMPARISON.md) — CounterLab versus Second Look, robotics and flood response; research, prior art, winners, and decision conditions.
2. [CounterLab PRD](COUNTERLAB_PRD.md) — full vision, actual submission scope, real cases, architecture, integrity requirements, and acceptance criteria.
3. [CounterLab delivery and evaluation](COUNTERLAB_DELIVERY_PLAN.md) — 42-hour baseline, early gates, baselines, withheld evaluation, resources, and demonstration plan.

## What is decided

- Audience: computational researchers, research engineers, and advanced AI learners investigating conflicting empirical results.
- Core: source evidence → competing predictions → committed experiment → measured result → revised explanation → reproduction bundle.
- Submission: two source-linked case views, at least one real discriminating investigation with verified protocol fidelity, adaptive follow-up, editable assumptions, and honest evaluation. Any second case with only source analysis or a mechanism demonstration is labeled accordingly.
- Full autonomous science is a long-term vision. Hosted P0 executes reviewed adapters, with supported scope clearly visible.
- Differentiation is a workflow hypothesis. Existing AI scientists and replication tools are substantial prior art.

## Preserved alternative: Second Look

The earlier recommendation remains intact as a narrower experiment-integrity product and delivery fallback: [PRD](docs/planning/PROJECT_PRD.md), [research](docs/planning/RESEARCH_AND_DECISION.md), and [delivery/evaluation](docs/planning/DELIVERY_AND_EVALUATION_PLAN.md). It has better present delivery confidence. CounterLab has the higher proposed ceiling only if its discriminating experiment loop works. No silent switch or claim that the original leakage demo fulfills CounterLab's vision is planned.

## What is not yet done

Basic setup is ready; no repeat account inspection is needed. Cumulative reported usage is 312,110 tokens across 52 inference calls. Last observed balance predates these runs and has not been rechecked. Stop-after-trial remains saved. Full source-regime fidelity, reliable model conclusions, the real disagreement investigation, demand validation, final model ranking, judging access and submission assets remain open. See [readiness tracker](READINESS_TRACKER.md).

Earlier development runs demonstrated bounded recovery after a rejected plan. The frozen benchmark now exposes reporting weaknesses that those examples did not reveal. Preserve this result while improving the workflow; do not represent reused tasks as a fresh evaluation.

The first two build sessions test feasibility. We will not treat the current performance targets as achieved or claim a win is guaranteed.

## Key dates

- Internal submission target: **October 29, 2026**.
- Official deadline: **October 30, 2026, 10:00 a.m. PDT / 1:00 p.m. EDT**.
- Keep the working demo available through **December 15, 2026**.

## Earlier preparation

[Preparation brief](docs/planning/HACKATHON_PREPARATION.md) and [readiness tracker](READINESS_TRACKER.md) retain the earlier preparation context. October 14 and October 15 recommendation/status statements describe those earlier phases; the October 16 documents above contain the current ambitious recommendation.

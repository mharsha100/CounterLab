# Open CounterLab

The local app is built and verified. Dependencies and the interface build are
already prepared in this workspace.

**October 25 current milestone:** **Research study → Source investigator** now
uses v2 for new starts. Predictions are committed, checked against necessary
conditions and rejected before worker execution when contradicted. The model
can use that feedback for one untried follow-up. A rejection is not a measured
result. Passing a necessary condition is not proof that a prediction is correct.

All 162 offline tests and the production build pass. The real restricted worker
boundary probe, two isolated numerical replays and actual HTTP export/fresh-process
replay also pass. No Nebius requests were made. Frozen v1 results and the prior
retrospective audit remain unchanged; v2 real-model quality has not been measured.

## Reference setup and publication preparation

New releases omit the full upstream numeric file, including inside nested replay
ZIPs. Core app inspection and the guarded live workflow work without it. The
source-reproduction view still checks the frozen three-row comparison but clearly
withholds the full-artifact identity check when that optional file is absent.

To opt into that check in a source checkout:

```powershell
.\.venv\Scripts\python.exe scripts\fetch_reference.py --download
```

The helper checks the pinned public HTTPS bytes before installing, never overwrites
an invalid existing copy, and makes no network request without `--download`.
A portable source replay uses `python fetch_reference.py --download` first. After
setup its replay is offline. `--local-file PATH` verifies a previous download.
No key, paid service or external algorithm execution is involved.

| New file | Purpose |
| --- | --- |
| `counterlab/reference_material.py` | Bounded optional data retrieval, exact hash verification and non-overwriting installation. |
| `scripts/fetch_reference.py` | Explicit reference status/download command; also included in the source replay. |
| `counterlab/public_distribution.py` | Recursively inspects release ZIPs for private files and the excluded full reference. |
| `.github/workflows/judge-pages.yml` | Manual-only Pages publication, prepared locally; no remote run or inference secrets. |
| `submission/PUBLICATION_GUIDE.md` | Publication scope, steps and public-access verification. |
| `submission/DEMO_NARRATION.md` | Honest narration for a 2:55 recorded-evidence demo. |

The evidence interface now links its full source ZIP. The GitHub workflow requires
an explicit manual run on main with publication confirmed; pushes do not deploy.
The remote repository, public URL and actual video still need completion.

## Portable evidence edition

Use the normal source app for live investigations. The evidence edition is a
separate static build for inspecting the same reviewed records without a backend.
It never starts a provider or worker and never falls back to a live API. JSON
hashes are checked in the browser; existing record checks ran at packaging.
The downloadable replay programs independently recompute the finite evidence.

New files and purposes:

| File | Purpose |
| --- | --- |
| `web/src/access.ts` | Selects normal API access or verified static snapshots; maps replay downloads under the hosting path. |
| `counterlab/judge_release.py` | Collects only reviewed records through the read-only API and builds allowlisted archives. |
| `scripts/build_judge_release.py` | Starts a new uniquely named local release; prints results and file hashes. |
| `scripts/serve_judge.py` | Standard-library verifier/server, copied into the portable ZIP as `serve.py`. |
| `tests/test_judge_release.py` | Checks tampering, private-file exclusion, missing records and static serving. |
| `submission/` | Judge guide, Devpost draft, tool feedback and remaining publication/recording work. |
| `LICENSE` / `THIRD_PARTY_NOTICES.md` | Our own-code MIT grant and the separate scope/provenance of dependencies and imported numeric data. |

Build commands are in README. Extract `counterlab-judge.zip`, run `python serve.py`
and open port 8002. `python serve.py --verify-only` checks package consistency.
The evidence browser works without Python on a static HTTPS host, once published.
Direct `file://` opening is unsupported. Neither build is publicly hosted yet.

## Guarded source workflow

For local inspection without credential loading, Docker or new investigations:

```powershell
.\.venv\Scripts\python.exe scripts\start_app.py --read-only --port 8001
```

Open **http://127.0.0.1:8001/?view=source-investigator**. The saved v2 example opens
first; the earlier v1 source record is still in the selector. This preview can
coexist with the normal server on 8000. Stop it with **Ctrl+C** when done.

### What the saved example shows

1. A **simulated** planner predicts that repeating exactly the same profile will
   change gate and miss counts. The input-only check rejects this contradiction;
   no worker was launched for proposal 1 and there are no measured counts for it.
2. The simulated follow-up selects the matched history intervention. Its outcome
   is not ruled out by necessary conditions, so the fixed worker runs it in two
   separate restricted containers at 150,000 requests.
3. Both copies and the host replay agree: 13,707 versus 13,963 post-warmup misses,
   and zero versus 801 gate credits. The backend derives a finite difference.
4. The example is integration evidence only. It uses zero real-model calls and
   does not add a successful Nemotron run to either benchmark.

### New records and portable replay

**Download investigation replay**, extract, then run:

```powershell
python replay.py
```

The standard-library Python 3.13 replay verifies the initial prompt, committed
plans, input-only decisions, saved feedback used by the follow-up, numerical
measurements, worker receipts and factual report. It requires no key, Docker,
network or model credits. Truncated responses are not retried. If a worker fails,
prior verified measurements remain in the report; any partial outputs are marked
unverified and cannot become observations. Hashes check consistency, not authorship.

The v2 workflow uses the unchanged v1 numerical task/worker. New UI starts use
`/api/source-investigations-v2`; historical v1 consent cannot be silently reused
for v2. Both versions share the one-active-job queue and idempotent request IDs.
The normal server must be restarted to load new endpoints. Starting any live run
still needs its explicit bounded credit consent; this milestone approves none.

### New files in plain language

| File | Purpose |
| --- | --- |
| `counterlab/source_guard.py` | V2 prompt, necessary-condition decision and canonical feedback/request construction |
| `counterlab/source_planner_v2.py` | Two-call planner that rejects contradictions before invoking the worker |
| `counterlab/source_run_record_v2.py` | Verifies complete decisions, request/feedback sequence, numerical results and portable export |
| `scripts/replay_guarded_source.py` | Becomes the credit-free `replay.py` in v2 downloads |
| `scripts/check_guarded_source.py` | Preview by default; `--docker` performs simulated planning plus real local boundary/worker/replay checks |
| `cases/paging/source_guarded_recorded_run/` | Verified simulated-planning example with actual Docker receipts and one measured target test |
| `tests/test_source_guarded.py`, `tests/test_source_guarded_api.py` | Contradictions, controls, truncation, partial failures, tampering, consent, version separation and replay checks |

Existing API and source-investigator UI files connect v2. App and research-view
files add the direct link. The frozen v1 planner, numerical kernel, worker and old
model-result files were not edited. The following tour and retrospective review
are the preceding, separate milestone.

## Guided demonstration

Keep the existing app open. Start a separate read-only instance:

```powershell
.\.venv\Scripts\python.exe scripts\start_app.py --read-only --port 8001
```

Open **http://127.0.0.1:8001/?view=demo**. No key or Docker is needed for inspection.
The server blocks both investigation start routes. Opening this mode does not
mark jobs in another server interrupted. Stop this instance with **Ctrl+C** when
you finish. It is local only; public judge hosting is still outstanding.

### Recording sequence — maximum three-minute draft

This is a rehearsal plan; a video has not been recorded or published.

| Time | Screen/action | Spoken point |
| --- | --- | --- |
| 0:00–0:20 | Guided demonstration, first step | “CounterLab helps researchers turn an implementation disagreement into a testable experiment. NVIDIA Nemotron 3 Ultra, served through Nebius Token Factory, proposes the test and predictions. The reviewed runner supplies the measurements.” |
| 0:20–1:00 | An experiment; open the saved hypothesis and point to counts | “This is a recorded real model response. Only history timing changes. The model-selected test replayed premeasured, independently checked evidence: 509 versus 510 misses and zero versus ten gate credits. The backend derives the finite finding from those counts.” |
| 1:00–1:40 | A failed prediction | “The model also makes mistakes. In this smaller case it predicted two differences, yet both counts agreed. A later check proves a difference was impossible here. That review was added after the batch, so the original failures and scores remain visible.” |
| 1:40–2:15 | A fair comparison | “We evaluated eight frozen tasks with adaptive and fixed model choices, a contract heuristic and seeded random selection. The adaptive model found both available finite differences, as did the baselines. We have not established an advantage over the heuristic. Two truncated responses remain failures.” |
| 2:15–2:50 | Replay it yourself; point to download and scope | “The package replays all 22 measured options, 45 independently checked profiles and every policy score with Python, without keys or credits. Finite results do not resolve the full paper disagreement or prove a theorem.” |
| 2:50–2:55 | Return to the product promise | “The useful result is an inspectable experiment and a scoped evidence trail, even when the AI's prediction is wrong.” |

The displayed tour is curated from previously explored examples. Do not present
it as a live model run or a new held-out success. Model test selection in this
batch consumed verified replay evidence; it did not measure fresh worker latency.
The full evaluation remains available from the comparison step.

### Download the later prediction review

Use **Download later prediction review**. Extract and run:

```powershell
python review_predictions.py
python replay.py
```

The first recomputes the retrospective audit. The second reruns the original
independent numerical checks and 32 policy scores. Both use standard-library
Python 3.13, no credentials, Docker, network or credits. Larger-cache predictions
are not called correct just because no contradiction was found. Hypothesis prose
and causal explanations are not verified by these Boolean checks.

### New files in plain language

| File | Purpose |
| --- | --- |
| `counterlab/prediction_review.py` | Checks whether a saved prediction contradicts necessary conditions; builds the separate review/export |
| `counterlab/demonstration.py` | Assembles the evidence tour from records that pass the existing verifier |
| `scripts/review_source_predictions.py` | Recomputes the later review without model calls; also becomes `review_predictions.py` in the download |
| `web/src/Demonstration.tsx` | Four-step recorded evidence tour |
| `web/src/PredictionReview.tsx`, `web/src/demonstration.css` | Plain-language prediction review and responsive tour layout |
| `tests/test_prediction_review.py`, `tests/test_demonstration.py` | Necessary-condition, independent-oracle, read-only, coexistence, verified-record and portable replay checks |

Existing `counterlab/api.py` and `scripts/start_app.py` expose the read-only mode;
existing interface files connect the tour and review. Frozen source planning,
worker, numerical code and original results were not edited.

## 1. Start it

From PowerShell in `C:\MY_PROJECTS\NVIDIAxNEBIUS`:

```powershell
.\.venv\Scripts\python.exe scripts\start_app.py
```

Keep the terminal open. Visit **http://127.0.0.1:8000**. Press Ctrl+C in the
terminal to stop. If needed, choose another port with `--port 8001`.
The server listens only on this computer.

**October 24 worker update:** Restart an already running app to load the new
backend. Keep Docker Desktop running for new investigations. The experiment
worker is already built and verified on this laptop; no setup command needs
repeating now. Recorded evidence remains available without Docker or a key.

## 2. Inspect the saved investigation

**New source reconstruction:** Select **Research study**, then **Source
reproduction**. This shows the three matched published aggregates at 150,000
requests, all ten matched history interventions, exact source settings, seeds
and fingerprints. The download reexecutes all 30 profiles plus independent
prefix checks; allow a few minutes. Viewing the page uses no inference.

Opening the app uses no model credits. Its initial example says **Recorded run**.

- **Investigation:** proposals, mathematical rejection, follow-up and measured results.
- **Sources:** four pinned references and inspected implementation contracts.
- **Research study:** six-source audit, all 416 finite profile results, conditional maps, counting windows and a full-study replay download. Viewing it uses no credits; its first load verifies the measurements.
- **Evaluation:** independent mathematical validation, the frozen eight-task comparison, all four policies, original failed answers beside checked interpretations, and a download that recomputes all measurements and scores. Viewing or replaying it uses no credits.
- **Evidence:** verified numbers, protocol, input cases and evidence download.
- **Run history:** the example and investigations started through the app.

Model explanations are unverified proposals. The runner checks measurements
against committed inputs before displaying them. The constructed paging case
does not reproduce the full published reports or establish a general model ranking.

## 3. Start a fresh investigation when needed

For the validated 150,000-request source regime, use **Research study → Source
investigator**. Review its four fixed tests, select the token allowance and
confirm credit use only when you intend to start a live run. Saved source
investigations are selected in that view. A repeat control cannot answer the
history question; its equality remains a separate observation. The server shares
one queue across source and constructed-case jobs, and binds duplicate request
IDs to their original workflow and token allowance.

The top-level **New investigation** button below refers to the older small,
constructed diagnostic:

Click **New investigation**, inspect the reviewed protocol and three allowed
input cases, select the output allowance, and confirm credit use. The default
allowance is 8,192 output tokens per request. New version-5 live behavior has not
yet been tested.

Limits: at most two Nemotron planning requests and two paired local experiments, with no
automatic retries. Token caps are not dollar spending limits. The saved Nebius
Stop-after-trial preference is unchanged. Closing the page does not cancel a run.

The key stays in backend `.env`; it is never sent to the browser. One active job
blocks a second investigation, duplicate submissions reuse the same request ID,
and failed attempts remain saved.

New app investigations and the `run_investigation.py --run` CLI use the local
Docker worker for experiment execution. It receives a small JSON input over
standard input, with no API credentials, host folders or Docker socket mounted.
Its limits are: no network, read-only root filesystem, unprivileged user, all
capabilities dropped, one CPU, 256 MB memory, 32 processes and 15 seconds wall
time. Only the reviewed numerical code is included. These use Docker's documented
[container controls](https://docs.docker.com/engine/containers/run/).

The backend checks availability before contacting the provider. If Docker stops
later, the run fails without an automatic retry or an in-process execution
fallback. Each accepted experiment saves an execution receipt with image ID,
code hashes, limits, input hash and evidence ID. Earlier runs are explicitly
labeled as predating this worker in the evidence drawer. Numerical verification
and standalone replay still use the reviewed local code. This worker accepts
fixed reviewed experiments; it does not execute arbitrary uploaded code.

## 4. Download and replay

Click **Download evidence** on the Evidence screen. Extract the ZIP and run:

```powershell
python replay.py
```

Replay requires Python 3.13 and its standard library. It checks hashes and reruns
accepted experiments without an API key, network connection or credits.

## What the new files do

The newest evaluation files are listed here; the earlier app and study files follow.

| Source reconstruction file | Purpose |
| --- | --- |
| `counterlab/source_regime.py` | Own frozen reconstruction of the selected original-scale source regime and matched history intervention |
| `cases/paging/source_regime/` | Selection saved before source values, frozen protocol, attributed numeric artifact, all seeds, receipts, comparisons and manifest |
| `scripts/prepare_source_regime.py` | Retrieves only the pinned public numeric data and metadata; already completed |
| `scripts/freeze_source_protocol.py` | Commits the exact settings and numerical code before full execution; already completed |
| `scripts/check_source_regime.py` | Checks initialization and events against independent prefix-optimal cache states |
| `scripts/run_source_regime.py` | Two isolated replays plus a host replay per seed, followed by the preregistered source comparison; already sealed |
| `counterlab/source_records.py` | Verifies the pinned record, published values and recomputed summaries; builds the portable ZIP |
| `scripts/replay_source_regime.py` | Reexecutes all ten seed batches by default; `--seed 0` explicitly performs a partial replay |
| `web/src/ResearchWorkspace.tsx`, `web/src/SourceReproduction.tsx`, `web/src/source.css` | Research-view switch and source comparison interface |
| `tests/test_source_regime.py`, `tests/test_source_records.py` | Reset/predictor/RNG checks, independent baselines, source-data integrity and portable replay tests |

These files add one selected supporting-report reconstruction. They do not
replace the frozen laboratory study, old model results or official paper code.

| New reporting file | Purpose |
| --- | --- |
| `counterlab/evidence_report.py` | Derives a complete finite factual report from verified counts and citations |
| `counterlab/verified_investigator.py` | Two-call planner; replays measurements before feedback and makes no final model call |
| `web/src/VerifiedFinding.tsx`, `web/src/finding.css` | Shows all measurements, their links and the original model answer separately |
| `scripts/check_reporting_regression.py` | Retrospective check over existing records; does not rescore models |
| `tests/test_evidence_report.py`, `tests/test_verified_investigator.py` | Checks conclusion distinctions, complete citations, truncation and fabricated-result rejection |

The existing API, record verifier and replay now save and verify
`evidence_report.json`. Numerical reference files, frozen task inputs and model
results were not changed. The older version-4 investigator remains for historical
tests and its mathematical preflight helper.

Version 5 passed 82 offline tests and real Docker/export checks with simulated
planning. Its retrospective audit covered 32 records and 42 citations. This is
integration verification, not a new model accuracy result. New live model
behavior has not been tested. Next validate planning on fresh frozen tasks when
a new bounded credit batch is approved, and resolve source and judging access.

| File or folder | Purpose |
| --- | --- |
| `counterlab/work_function_oracle.py` | Independent mathematical checker using reachable cache configurations |
| `scripts/check_work_function_fidelity.py` | Checks all study events and exhaustive small profiles; already completed |
| `cases/paging/oracle_validation/` | Frozen validation plan, event fingerprints and result receipt |
| `counterlab/evaluation_suite.py` | Frozen candidate tests, admission rules and separate scoring definitions |
| `counterlab/evaluation_agent.py` | Bounded adaptive and fixed-plan model policies |
| `scripts/prepare_agent_evaluation.py` | Freezes task inputs and scoring before seeing outcomes; already completed |
| `scripts/prepare_evaluation_environment.py` | Collects double Docker measurements, independent checks and simple baselines; already completed |
| `scripts/run_agent_benchmark.py` | Runs one explicitly approved batch; refuses a second launch; already completed |
| `cases/paging/agent_evaluation/` | Public frozen inputs, hidden-environment measurements, baselines, actual model results and fingerprints |
| `counterlab/evaluation_verification.py` | Recomputes measurements and scores, rejecting fabricated values even if hashes are rewritten |
| `counterlab/evaluation_records.py` | Verifies evaluation records, adds checked interpretations and builds the portable download |
| `scripts/replay_evaluation.py` | Download's standard-library replay; makes no model calls |
| `web/src/Evaluation.tsx`, `web/src/evaluation.css` | Evaluation screen and its responsive layout |
| `tests/test_evaluation_agent.py`, `tests/test_evaluation_records.py`, `tests/test_work_function_oracle.py` | Policy, integrity, export and mathematical boundary checks |

The model's exact response metadata, saved plans, commitments and request ledger
also remain under `artifacts/runs/agent-evaluation/`. Those are execution records,
not another project or additional required setup. Do not rerun the paid batch.

| File or folder | Purpose |
| --- | --- |
| `counterlab/api.py` | Local API, persistent jobs, credit-use consent and app serving |
| `counterlab/records.py` | Record integrity, numerical verification and evidence ZIPs |
| `web/src/` | React/TypeScript screens, API connection and responsive styling |
| `web/package*.json` | Frontend dependencies, exact lock and build commands |
| `requirements*.txt` | Python runtime, test dependencies and exact installed lock |
| `scripts/start_app.py` | Starts the complete app with one command |
| `scripts/prepare_recorded_run.py` | Prepares the reviewed portable example; already done |
| `scripts/replay_record.py` | Offline replay, included as `replay.py` in downloads |
| `worker/` | Pinned Python image recipe and fixed numerical JSON interface |
| `counterlab/experiment_worker.py` | Starts bounded containers, validates evidence and saves receipts |
| `scripts/setup_worker.py` | Builds an image from an allowlist; project secrets never enter its build context |
| `scripts/check_worker.py` | Real Docker boundaries, six replays and app/export verification with simulated inference |
| `artifacts/worker/` | Ignored local image ID and source lock |
| `cases/paging/recorded_run/` | Deliberately checked-in example and integrity manifest |
| `tests/test_api.py` | API, duplicate-run prevention, integrity and export/replay tests |
| `counterlab/protocol_study.py` | Independent runner for the three behavior settings and both counting windows |
| `cases/paging/protocol_study/` | Frozen protocol, complete observations, source facts, original execution plan, receipts and manifest |
| `counterlab/study_records.py` | Verifies study measurements and creates the portable export |
| `web/src/ResearchStudy.tsx` | Source comparison, conditional map, scenario explorer and witness explanation |
| `scripts/audit_paging_sources.py` | Inspects six pinned source files as text/syntax trees; requires the existing source cache |
| `scripts/prepare_protocol_study.py` | Commits the study protocol; already done |
| `scripts/run_protocol_study.py` | Runs two isolated replays of each frozen batch; already done |
| `scripts/replay_study.py` | Full-study numerical replay, delivered as `replay.py` in its export |
| `artifacts/app/` | Ignored local job database and replay verification outputs |
| `artifacts/ui/` | Ignored browser-verification screenshot |

## Fresh-checkout setup

Use Python 3.13 and a compatible Node.js installation:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
npm.cmd --prefix web ci --no-fund --no-audit
npm.cmd --prefix web run build
.\.venv\Scripts\python.exe scripts\setup_worker.py
.\.venv\Scripts\python.exe scripts\start_app.py
```

The recorded view works without a Nebius key. Configure `.env` only for live use.
No downloaded external algorithm source or credential is in the portable example.
The worker setup needs Docker Desktop in Linux-container mode and downloads an
official, digest-pinned Python image. It uses no Token Factory credits or cloud
compute. Rebuild the worker after deliberately changing its reviewed code.

## Source workflow file map

| File or folder | Purpose |
| --- | --- |
| `counterlab/source_investigation.py` | Fixed source test menu, admission, measurement binding and complete factual ledger. |
| `counterlab/source_planner.py` | Two-turn planning loop; saves predictions before execution and retains failures. |
| `counterlab/source_run_record.py` | Reexecutes accepted source measurements, checks receipts/report and creates the portable download. |
| `scripts/replay_source_investigation.py` | Credit-free replay entry point, included as `replay.py` in the ZIP. |
| `cases/paging/source_recorded_run/` | Clearly labeled simulated-planning example with four real Docker executions. |
| `web/src/SourceInvestigator.tsx` | Source-specific approval, progress, saved runs, measurements and factual report. |
| `scripts/prepare_source_evaluation.py` | Freezes fresh derived inputs and evaluation rules without measuring answers. |
| `cases/paging/source_planning_evaluation/protocol.json` | Eight frozen, unrun diagnostic tasks; not a new model score. |
| `scripts/preview_source_investigator.py` | Local QA only: simulated source planning and actual Docker experiments, no key read. |
| `tests/test_source_investigator.py`, `test_source_investigation_api.py`, `test_source_evaluation_preparation.py` | Failure, consent, replay, provenance and fresh-task preparation checks. |

## Fresh evaluation file map

| File or folder | Purpose |
| --- | --- |
| `counterlab/source_full_oracle.py` | Independent cache-cost states; checks every event without the production layer algorithm. |
| `counterlab/source_evaluation.py` | Fixed task verification, evidence-free baseline orders and separate scores. |
| `counterlab/source_evaluation_agent.py` | Adaptive and fixed policies; saves fixed choices before feedback and counts unused calls. |
| `counterlab/source_evaluation_records.py` | Replays measurements, rechecks scores and creates the portable evaluation export. |
| `scripts/freeze_source_execution.py` | Seals execution, policy and scoring rules before outcomes. |
| `scripts/prepare_source_environment.py` | Two Docker runs per admissible option, full independent checks and both baselines; refuses sealed recollection. |
| `scripts/run_source_evaluation.py` | Preview without credentials; one explicitly approved batch with a shared 32-call ceiling and no retries. |
| `scripts/replay_source_evaluation.py` | Complete offline replay entry point included as `replay.py` in the download. |
| `cases/paging/source_planning_evaluation/` | Frozen task/execution rules, all reference outcomes, receipts, independent checks and separate model results. |
| `web/src/EvaluationWorkspace.tsx`, `SourceEvaluation.tsx` | Separate original/fresh evaluation views and reference-outcome inspection. |
| `tests/test_source_full_oracle.py`, `test_source_evaluation_agent.py`, `test_source_evaluation_records.py` | Full-trace, policy sequencing, truncation, cost accounting, tamper and replay checks. |

## Verified and remaining

All 123 offline tests and the production build pass. Browser verification covered
narrow/desktop layouts, source navigation, the evidence drawer, credit consent,
live progress, saved history and actual download. The downloaded live ZIP passed
standalone numerical replay with zero inference requests.

Browser run `484d66ce958442b9a84cf1b140123984` completed in 28.487 seconds,
using three requests and 17,651 tokens. It rejected case_3, correctly predicted
case_1 differences, and displayed 1/0 gate credits and 19/18 misses. It is saved
in local run history; the portable example is the earlier verified run.

The actual worker boundary check and six numerical comparisons passed. A separate
app job with a simulated provider executed in Docker, saved its receipt, sealed
its record and exported a bundle that replayed offline. This consumed zero model
credits. Evidence: `artifacts/runs/worker-check/d011c91d5963471180071259d81cd869/summary.json`.

The new study froze 52 scenarios and tested all eight behavior combinations:
416 profile runs, each replayed twice in Docker, with 624 matched comparisons.
All four controls and host numerical verification passed with zero inference.
History, priority and prediction delivery each affect some finite outcomes;
effects can reverse direction or disappear. All results, including null cases,
are retained. The original execution plan and source audit are bound into the
download. It replays with standard-library Python, without Docker or a key.

Browser checks cover factor/advice controls, scenario selection, cost windows,
correct 0/0 handling, desktop/narrow layouts and a clean error console.

The frozen agent benchmark completed with 36 calls and 240,279 reported tokens.
Adaptive found 2/2 available differences, fixed-plan found 1/2; both simple
baselines found 2/2 with fewer tests and no inference. Fully correct model findings
were only 3/8 and 1/8, respectively. Two truncated responses remain failures.
The UI keeps original answers visible and independently computes the checked
interpretation; it does not rewrite the original score. One repeat and one
adapter cannot establish a general model ranking. The evaluation download
recomputes 21 paired measurements and all 32 run scores offline, and verifies
the independent oracle validation receipt without rerunning all 161,872 events.

The source-linked workflow and fresh frozen evaluation are complete at the
documented scope. The model does not yet beat the contract heuristic; prediction
checks need strengthening before broader reliability claims. The next product
work should address those checks, judging access and submission/demo assets.
Any prompt changes require fresh evaluation conditions; do not rescore the
original suite as a new holdout. Broader source fidelity remains open.
See
[source audit](cases/paging/SOURCE_AUDIT.md). No hosting was provisioned.

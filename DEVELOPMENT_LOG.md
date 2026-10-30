# CounterLab — development log

This is the complete, dated build history that previously formed the README. It is kept
verbatim for auditability: test counts and usage figures in each milestone are historical.
For the current overview, setup and results, start with [README.md](README.md).

---


Turn disagreement into experiments. Planned hackathon track: Best Apps and Agents,
with NVIDIA Nemotron inference through Nebius Token Factory.

## Completion countdown

The fixed project-first checklist is in [PROJECT_COUNTDOWN.md](PROJECT_COUNTDOWN.md).
Each completed work batch reports the remaining steps.

## Fresh installation — current instructions

Extract the full source ZIP into a new folder and open PowerShell there:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe scripts\check_readiness.py
.\.venv\Scripts\python.exe scripts\start_app.py --read-only --port 8001
```

Open **http://127.0.0.1:8001/**. The compiled interface is included. Recorded
inspection and the bounded workbench require neither Node, Docker, an API key
nor the optional full upstream reference. Installation downloads dependencies;
read-only startup makes no model request and blocks all investigation starts.
Use another port if 8001 is occupied; do not stop an existing app unnecessarily.

For development, `npm.cmd --prefix web ci --ignore-scripts` installs the locked
frontend packages; `npm.cmd --prefix web run build` rebuilds the app and
`npm.cmd --prefix web run build:judge` builds the separate portable edition.

The **complete test suite** additionally uses the optional pinned numeric
reference as a fixture. Install it explicitly before running the suite:

```powershell
.\.venv\Scripts\python.exe scripts\fetch_reference.py --download
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
npm.cmd --prefix web run test:all
```

Alternatively, `scripts\fetch_reference.py --local-file PATH` verifies an
already downloaded copy without network access. The full upstream file is
excluded from releases. See [release validation](submission/VALIDATION.md) and
[project freeze](submission/PROJECT_FREEZE.md) for current evidence; test counts
and usage figures in the dated implementation milestones below are historical.

## Check local setup

```powershell
.\.venv\Scripts\python.exe scripts\check_readiness.py
.\.venv\Scripts\python.exe scripts\start_app.py --read-only --port 8001
```

The setup check explains missing packages or an out-of-date interface build.
It does not open API keys, contact Nebius or spend credits. Add `--worker` to
inspect the local Docker image without running an experiment. Inspection can
work without Docker; provider access and credit balance are deliberately unknown.
The launcher runs the same required checks before starting. Rebuild a stale
interface with `npm.cmd --prefix web run build`. File fingerprints detect local
changes; they are not signatures or independent build attestations.

Only one writable app may own a workspace. Open additional viewers with
`--read-only`; they cannot interrupt or start an investigation. When upgrading
from an older build, stop its live server before starting the new live build,
because the older process does not hold the new workspace lock. Closing a browser
tab does not stop a running investigation.

The final quality review is recorded in
[FINAL_PROJECT_REVIEW.md](submission/FINAL_PROJECT_REVIEW.md). Dated milestones
below retain earlier counts; use the current review and release receipt for
the accepted version.

## Private demo rehearsal

A ten-scene private review cut is prepared locally: about 2:41, 1080p, captions
and a labeled synthetic guide voice. It uses edited captures of the working
interface. The timed script is in [submission/DEMO_NARRATION.md](submission/DEMO_NARRATION.md).
Local media and its review kit stay under `artifacts/demo/20261026-review/` and
are excluded from the source release. Final continuous recording, chosen final
narration and public YouTube upload remain pending. No new model calls were used.

## Audit the claims

Open **Sources → Claim audit** (`?view=claim-audit`). Five bounded questions link
source contracts, selected reference rows, matched timing interventions and the
complete four-policy evaluation. Each answer includes its scope, exact record
fields, comparability checks and missing evidence. Unknown coverage stays unknown;
no model-selection advantage or full-report verdict is asserted.

Save the audit JSON, then recheck it against the verified local records:

```powershell
.\.venv\Scripts\python.exe scripts\check_claim_audit.py --record PATH_TO_JSON
```

This rederives the statements; a recomputed hash cannot legitimize edited claims.
The optional full-reference verification context is separate from the frozen
three-row comparison. This is developer-framed, deterministic evidence inspection,
not autonomous claim extraction. No model, Docker or reference download is used.

## Design a bounded experiment

Open **Research study → Design an experiment** (`?view=experiment-workbench`).
Edit synthetic requests, cache size, seeds, forecasts and budget, then commit
predictions before comparing the two history rules. The unchanged pinned Python
engine measures both arms; LRU and the future-aware offline optimum add context.

These are **human-designed synthetic diagnostics**, separate from the source
slice and frozen model benchmark. The local read-only calculator allows at most
512 requests and 16 slots, writes no workspace files and uses no model or Docker.
This open view retains up to ten completed comparisons; export before leaving.
Editing a draft does not relabel an earlier result.

The portable browser edition prepares plans without executing them. Save its
committed plan and checksum-checked runner in a new folder, then use Python 3.13:

```powershell
python counterlab-experiment.pyz counterlab-plan.json --output counterlab-result.json
python counterlab-experiment.pyz counterlab-result.json --verify
```

Only Python's standard library is needed. The runner includes our MIT license,
checks pinned engine bytes, refuses output overwrite and rejects rehashed
fabricated observations on replay. The protocol hash is not a trusted timestamp.
This update passed **201 offline Python tests and 12 frontend tests**. Run the
frontend gates with `npm run test:downloads --prefix web` and
`npm run test:workbench --prefix web`.

## Evidence library

Open **Evidence → Evidence library** for all eight reviewed replay packages.
Cards distinguish real model records, simulated planning and deterministic
analysis, and explain each package's scope and replay command. The source-slice
package explicitly lists its separate reference-data setup.

Choose **Check package**, then **Save checked ZIP**. The browser checks size,
ZIP signature and SHA-256 before preparing the download. The portable edition
uses its release manifest; the local app uses the checksum for that exact server
response. Save the file-check receipt if useful. These are byte checks; extract
the ZIP and run its Python command for numerical verification.

The library update passed **191 offline Python tests**, **eight browser-download
unit tests**, and both interface builds. Run the download tests with
`npm run test:downloads --prefix web`. No additional dependencies or model calls
are needed. The private GitHub update is pending reauthentication after HTTP 401;
the original private upload remains unchanged.

## Start with the evidence

The app opens the guided tour by default. In its first step, select **Open trace
explorer** to inspect the cache one request at a time. Jump to the first history,
decision or hit/miss difference; compare two controls; inspect the gate calculation
and download the three traces. These are explicitly labeled original constructed
diagnostics, separate from the source-evaluation task above them.

The local Python runner recomputes every state from the pinned algorithm. The
portable edition shows the same states verified at packaging time. Both use zero
model calls. To reproduce the trace from source, run:

```powershell
.\.venv\Scripts\python.exe scripts\inspect_trace.py
```

Add `--output artifacts/diagnostic-traces.json` to save a new JSON file without
overwriting an existing one. All **187 offline tests** and both builds passed
for this update. The witness remains 19 versus 18 misses; the controls agree.

## Private GitHub repository

The reviewed source is uploaded to [mharsha100/CounterLab](https://github.com/mharsha100/CounterLab).
It is **private**. Commit `a9fe693cbc979c33097b824b8a6049c34788bd40` on `main`
contains all 295 files of the prior frozen source package. The final quality-review
changes are local and have not been uploaded to that commit. Public source/site
access still needs a later explicit instruction. The verified upload receipt is
under `artifacts/releases/counterlab-private-sync-20261026/`.

## Portable evidence release — October 25

A separate keyless build now packages the reviewed records and replay downloads.
It labels recorded results, performs browser JSON integrity checks and has no
live API fallback. The full source ZIP includes the compiled normal interface.
Neither archive contains `.env`, private run history, downloaded external code,
`node_modules` or your virtual environment.

Build locally (no inference, Docker or publication):

```powershell
Set-Location web
npm run build
npm run build:judge
Set-Location ..
.\.venv\Scripts\python.exe scripts\build_judge_release.py
```

The builder prints a unique directory under `artifacts/releases/` containing
`counterlab-judge.zip`, `counterlab-source.zip` and hash manifests. Extract the
judge ZIP and run `python serve.py`; open **http://127.0.0.1:8002/**. Python's
standard library is sufficient. See [judge instructions](submission/JUDGE_GUIDE.md).

[Submission draft](submission/DEVPOST_DRAFT.md), [tool feedback](submission/TOOL_FEEDBACK.md)
and [completion/recording plan](submission/RELEASE_CHECKLIST.md) are prepared locally.
All 181 offline tests passed for the preceding publication-preparation update. Both
interface builds pass. The earlier portable release also passed desktop/mobile,
extracted source inspection and actual HTTP evaluation replay. See
[validation details](submission/VALIDATION.md). Public repository, judge URL and
video are still pending. New packages omit the full upstream numeric artifact;
optional hash-verified reference setup is documented in
[third-party notices](THIRD_PARTY_NOTICES.md). See the prepared
[publication guide](submission/PUBLICATION_GUIDE.md) and
[narration script](submission/DEMO_NARRATION.md). Our own code has an MIT license; third-party material is excluded
from that grant. No new model calls or paid services were used for this milestone.

## Open the app

The Python API and React/TypeScript interface are built and verified. From this
project folder:

```powershell
.\.venv\Scripts\python.exe scripts\start_app.py
```

Open **http://127.0.0.1:8000**. Startup and recorded inspection use no credits.
New investigations require reviewing the approved cases and confirming credit use.
See [APP_GUIDE](APP_GUIDE.md) for screens, new-file purposes, evidence replay and setup.

Keep Docker Desktop running for new investigations. The local isolated worker
is already built in this workspace; fresh checkouts use `scripts/setup_worker.py`.
Restart a running server to load the worker integration.

All 162 offline tests and the production build pass. A real browser-to-API run
completed, and its downloaded ZIP replayed successfully without inference. This
is a local app. The Docker worker now passes boundary, six replay comparisons,
and simulated-provider app/export checks with no new inference. Full research
reproduction, broader external evaluation and deployment remain open.

## Guarded source workflow v2 — October 25

**Research study → Source investigator** now checks predictions before worker
execution. Contradictions become saved rejection feedback, not measured outcomes.
The new version retains the two-call cap, no retries and complete factual report.
It has a separate start/consent route; the old workflow and scores remain intact.

```powershell
.\.venv\Scripts\python.exe scripts\start_app.py --read-only --port 8001
```

Open **http://127.0.0.1:8001/?view=source-investigator**. The new saved example is
simulated planning with two real isolated numerical replays: an impossible
repeat prediction is blocked, then a valid history intervention is measured.
The portable download rechecks decisions, request/feedback order and measurements
without keys, Docker, network or credits. Zero new model calls were made; v2
model quality and external judge hosting remain open.

## Guided demonstration and prediction review — October 25

Open **Guided demonstration** for recorded real Nemotron responses, a verified
experiment, a failed prediction and the complete four-policy comparison.
The later review identifies 14 contradictory model plans using only the input
contract, not measured answers. It is a retrospective development audit: old
scores and numerical files remain unchanged. No model improvement is claimed.

```powershell
.\.venv\Scripts\python.exe scripts\start_app.py --read-only --port 8001
```

Open **http://127.0.0.1:8001/?view=demo**. Read-only mode blocks experiment starts,
skips credential loading and does not require Docker. The app is still local;
external judge access is not deployed. The review download retains all original
evaluation evidence and adds a separate reproducible audit. Desktop/mobile and
actual HTTP export/replay passed. Zero new inference.

## Fresh source evaluation — October 24

Open **Evaluation → Fresh source evaluation**. All 22 admissible reference
options ran twice in restricted containers. A separate cache-cost-state oracle
matched all **45 distinct profiles and 145,041 post-warmup events**, across
their full traces. Every null, control and mismatch direction remains available.
Both zero-inference baselines found the two available finite differences.

Task protocol `4b14936ae5db4dbb5fcb8feaf83c0017668b57fb3a09979b275b8c661b978ce5`
and execution protocol
`bf6ae1f4813dcd4f17619d528b2f818ba6726393ccdf1319c16705dc6db53e7b`
were frozen before the fresh outcomes were measured. Adaptive and fixed choices
share the frozen production planner and factual reporter; fixed choices are
committed before any execution feedback, including paid-for unused responses.
The downloaded replay reexecutes the full independent validation and every score
with standard-library Python and no credentials, Docker, network or credits.

The approved eight-task / two-policy batch completed with **27/32 calls**, no
retries and **101,300 reported tokens** (35,429 input / 65,871 output). All
returned models were exactly `nvidia/Nemotron-3-Ultra-550b-a55b`.

| Policy | Finite differences found / available | Both predictions correct | Model calls |
| --- | ---: | ---: | ---: |
| Nemotron adaptive | 2 / 2 | 2 / 11 | 13 |
| Nemotron fixed choices | 1 / 2 | 1 / 10 | 14 |
| Contract heuristic | 2 / 2 | 9 / 12 | 0 |
| Seeded random | 2 / 2 | 8 / 11 | 0 |

Two fixed-policy responses exhausted their output limit; both remain failures.
Adaptive used 11 target tests and two rejected choices; the heuristic used 11
target tests, one control and one rejection. **No selection advantage over the
heuristic is established.** Predictions remain unreliable. Factual reports are
shared backend checks, not model reasoning scores. One known-generator repeat
does not establish a general ranking or theorem verdict. Original scores are
unchanged. Cumulative reported inference is 413,410 tokens across 79 calls;
no remaining allowance is automatically reusable.

## Source investigator — October 24

Open **Research study → Source investigator**. The source-linked workflow has
at most two planning calls, two accepted tests and four isolated worker launches.
Nemotron commits predictions before execution and receives measured feedback.
The backend checks both worker replays against the frozen source kernel and
derives the factual report. A repeat control stays in the ledger but cannot
establish agreement for the history intervention. A budget-only change is
rejected as irrelevant to that question. Old constructed-case runs still work.

A saved **simulated-planning integration check** opens without credits: repeat
control → history intervention, at 150,000 requests. It shows 13,707 versus
13,963 misses and 0 versus 801 gate credits, with both measurement citations.
Four actual Docker executions and a full downloaded replay passed. This tests
the integration; it does not measure Nemotron planning performance. Starting a
new live run requires separate, explicit credit consent in the source view.

Eight new source-derived evaluation conditions and fair scoring/budget rules
are frozen in `cases/paging/source_planning_evaluation/protocol.json`.
Their numerical environment and separately approved live evaluation are now
complete as described above. The earlier integration milestone used
no live inference, and its saved example remains explicitly simulated planning.

## Source reconstruction — October 24

Open **Research study → Source reproduction**. We independently reconstructed
three selected supporting-report E4 aggregates at their original settings:
uniform requests, k=16, 150,000 requests, inverted forecasts and ten algorithm
seeds. The source's warmup reset, RNG schedule, stored forecasts and count window
are reproduced explicitly. All three OPT/mean/std comparisons match; the observed
mean and standard-deviation residuals are zero (frozen tolerance 1e-12).

| Selected source row | Reported ratio | Our ratio |
| --- | ---: | ---: |
| OnOPT-OM | 4.325495 | 4.325495 |
| RPB-OM, budget reset 1 | 5.261395 | 5.261395 |
| Source LRU control | 3.418064 | 3.418064 |

Changing only history refresh from every request to after misses adds **247–285
misses** in all ten matched seeds (mean +259.5). Each pair shares the same trace,
forecasts, priorities, initialization and counting window. This is a finite
intervention result; it does not establish a general algorithm ranking.

Thirty profiles ran twice in isolated containers and matched a host replay.
Independent prefix/state validation covered 530 profiles and 5,160 events. The
download reexecutes all 30 full-length profiles and the oracle checks with only
Python's standard library. Viewing the page verifies the anchored record,
published numeric artifact and aggregates; full reexecution belongs to the replay.

This closes the selected supporting-source slice check. Full paper/official-code
parity, the challenging report's adversary, other regimes and the asymptotic
claim remain open. The developer chose this experiment; no new model contribution
or model score is claimed. No external algorithm code was executed or exported.
No new live inference or credits were used.

## Frozen agent evaluation — October 24

### Reporting update after that evaluation

New investigations use `history_timing_v5_evidence_derived_report`: Nemotron
commits predictions and chooses at most two tests. The backend replays every
accepted measurement, then derives the finite factual report without a final
model call. Every observation is cited, including agreement before a follow-up.
A rejected prediction is not an observation. Agreement, absent measurements,
non-comparability and asymptotic insufficiency remain distinct.

The interface exposes each metric, its evidence fingerprint and a link to the
original measurement. Earlier model answers remain separately inspectable.
Version-5 downloads also replay the complete report; altered or omitted
measurements fail verification even when file hashes are rewritten.

Both rejected-plan recovery and a real Docker null-result → difference path
passed with simulated model planning. The latter retained both measurements in
its portable export. Simulated runs are explicitly labeled. No new live model
requests were made for this update. A retrospective integration audit covered
32 existing records and 42 citations; this is not a fresh agent benchmark and
does not improve the frozen scores below or establish better planning.

Current gate: 92 offline tests, production build, real Docker integration and
standalone factual-report replay pass. Live version-5 model behavior remains
untested. Source-regime fidelity and judging access remain open.

Open **Evaluation** in the app. The numerical engine passed 161,872 event
comparisons against a separate cache-configuration oracle that does not reuse
its layer representation. A frozen eight-task experiment-selection diagnostic
then completed using 36 of 40 approved model calls, with no automatic retries.

| Policy | Available differences found | Fully correct scoped findings | Tests | Model calls |
| --- | --- | --- | --- | --- |
| Simple heuristic | 2/2 | 8/8 | 10 | 0 |
| Seeded random | 2/2 | 8/8 | 10 | 0 |
| Nemotron fixed plan | 1/2 | 1/8 | 11 | 15 |
| Nemotron adaptive | 2/2 | 3/8 | 11 | 21 |

The baselines use a deterministic numeric reporter; their finding scores are
not LLM summarization scores. Two model runs truncated. Nulls, missing evidence
references and incorrect conclusion labels are preserved. Only two finite tasks
had an available difference; no favorable cases were substituted after execution.
There is **no demonstrated advantage over the simple selection baselines**.
This run does not meet the planned autonomous reporting release target.

The UI shows the original model answer alongside a separately computed checked
interpretation. Downloading the evaluation recomputes all 21 paired tests and
32 stored run scores with Python's standard library. It checks the full oracle
validation receipt without repeating all its event comparisons. No replay uses
credits or regenerates model replies. Task outcomes are now development data;
future tuning cannot call these tasks a fresh holdout.

This is one repeat, one adapter and known generators with new seeds. Results
are replay-based: Docker measured the environment before evaluation and the
model received each result only after selecting that test. Full report fidelity,
external implementation parity and general model quality remain unestablished.

## Research study

Open **Research study** in the app. Six pinned sources are audited as text. A
frozen finite protocol covers 52 scenarios and eight combinations of history,
priority and prediction-delivery rules: 416 profile runs, each replayed twice in
Docker, and 624 matched comparisons. All four controls pass. Both miss-counting
windows and null results remain visible. The full download replays with Python
3.13 and its standard library, with zero inference.

The study quantifies finite mechanisms and input-dependent effects. It does not
establish external source-code parity or reproduce the full reports. The separate
agent evaluation above measures diagnostic variants. See [source audit](cases/paging/SOURCE_AUDIT.md).

## Current state

Local development setup, a real Lightning connection test, and a synthetic forced
tool/JSON round trip have passed. This repository now includes an independently
written paging baseline engine and an offline correctness/replay check.

An independently written exact-layer RPB-OM reference is now implemented and has
passed finite mathematical checks. A bounded adaptive development loop has now
completed one live investigation with Ultra. Matching external reproduction protocols, the real
disagreement investigation, broader external evaluation and deployment remain
pending. Generated traces are diagnostic checks, not published benchmark results.

## Verified investigation loop

The user's screenshot confirms a $50 account balance, a separate $0.99 trial
balance with 26 days left, and the Stop-usage-after-trial setting. Both $25 grants
have been applied. Partner service claims remain separate.

The revised comparison `29e6b94954a74ba0bdbf534d9cd023ef` again found Ultra
choosing case_3 and predicting differences that were absent. Its final numbers
were correct. Super VL used 8,144 reported reasoning tokens within its 8,192-token
completion allowance and ended with `length`; a tool-call field was present but
the incomplete response was not executed. This is no completed Super VL plan.
Do not repeat the comparison unchanged or keep raising caps.

Ultra is the provisional integration choice because its tool calls and evidence
answers complete. Its independent planning has failed this development task;
this decision does not establish a general quality ranking.

The first adaptive run `c5074e97a02a4fd0ad5eef8574d4e063` stopped before
execution: native tool arguments failed local schema checks after the full 4,096
completion-token allowance was used. The old run did not preserve argument-shape
diagnostics, so the exact offending field cannot be recovered.

Version `history_timing_v4_structured_plan_and_followup` now requests plans using
schema-constrained JSON, validates them locally, and invokes the same reviewed
backend adapter. This uses Nebius's documented
[structured-output mode](https://docs.tokenfactory.nebius.com/ai-models-inference/json).
It is not native autonomous function calling. Invalid-response field shapes and
budget metadata are saved without raw reasoning or unknown field values.

The workflow checks proposed predictions against necessary mathematical
conditions before running a local experiment. It rejects impossible predictions
with a reason, preserves the attempt, and gives Nemotron one follow-up choice.
A genuine control result also allows a follow-up. A rejected plan is not counted
as a measurement. The checker derives bounds from inputs; it does not contain
case-ID answers or previous observations. This is tool-assisted development reuse.

The assistant then verified one live run, `6c178e6a60f04b23983c98e3ccf7c51a`:
Ultra's case_3 plan was rejected mathematically; it selected case_1 on its follow-up,
predicted both differences correctly, and reported the measured values accurately.
Miss-based history had 1 gate credit and 19 misses; request-based history had
0 credits and 18 misses. The run used three requests, 15,390 tokens and 21.039 s.
Its final scope remained a development diagnostic, with insufficient evidence for
the full published disagreement. Initial planning remains weak; its proposed
narrative also misdescribed the witness as a repeated cycle. Treat model hypotheses
as proposals, not verified source facts. No repeat live check is needed.

Offline preview (zero requests; reads no credentials):

```powershell
.\.venv\Scripts\python.exe scripts\run_investigation.py --max-output-tokens 8192
```

The successful command is retained for reproduction, not a required next step:

```powershell
.\.venv\Scripts\python.exe scripts\run_investigation.py --run --max-output-tokens 8192
```

This uses `nvidia/Nemotron-3-Ultra-550b-a55b`, at most three inference requests,
8,192 output tokens per request, at most two local experiments, and no retries.
The code default stays 4,096; the larger cap requires the explicit option.
It checks the account catalog first. It changes no billing preference or `.env`
model default. Results are preserved under `artifacts/runs/investigation/`.
`development_investigation_completed` means a discriminating development result
and a grounded, scoped final finding; all earlier failures remain in `attempts`.
It does not mean the initial prediction was correct, the paper was reproduced,
or the full scientific and agent-contribution gates passed. An inconclusive or
needs-review result must be inspected rather than blindly rerun.

Workflow files and their purposes:

- `counterlab/adaptive_investigator.py`: feasibility checks and bounded follow-up.
- `scripts/run_investigation.py`: offline preview and explicit live entry point.
- `tests/test_adaptive_investigator.py`: verifies recovery, honest scoring,
  truncated-response rejection, call limits and credential-free preview.

All 34 offline tests and the real preview passed October 24. The assistant made
one live inference run after the restricted-network catalog attempt failed; the
catalog-only failure made no inference requests. The local API/interface milestone
is now implemented and verified in [APP_GUIDE](APP_GUIDE.md). Worker isolation and
full source-regime fidelity remain separate requirements; development recoveries
do not complete G1/G2.

## Completed model-comparison history

The user completed live run `bf71c66cceda4ff887489db87d75bacb`: Ultra selected
the perfect-advice control, predicted differences incorrectly, then accurately
reported the measured absence of differences. Super VL exhausted its 4,096-token
output budget before supplying a usable plan; its scientific reasoning was not
scored. Neither result selects a final model. Three calls used 11,833 tokens.

Our original prompt omitted layer transitions and the precise assignment of Y.
Version `history_timing_v2_complete_rules` now supplies those general rules without
past observations or case answers. This is a revised development task, not an
independent holdout or a directly comparable rerun of the original prompt. All
original artifacts remain intact. Both models receive the same revised input,
automatic tool choice, sampling settings and explicit output cap.

Historical comparison preview (not the current next step):

```powershell
.\.venv\Scripts\python.exe scripts\compare_nemotron.py --max-output-tokens 8192
```

Expected status: `model_comparison_plan_ready`. The already-completed live command
is retained for reproducibility; do not repeat it unchanged:

```powershell
.\.venv\Scripts\python.exe scripts\compare_nemotron.py --run --max-output-tokens 8192
```

The live command checks the account model catalog, then makes at most four inference
requests: two per model, capped at 8,192 output tokens each, with no retries.
The default remains 4,096 unless the larger budget is explicitly requested.
Optional `--model` accepts one of the exact listed IDs to test only that model,
reducing the maximum to two calls. No failed call triggers a budget increase.
Sampling is temperature 1.0/top_p 0.95; provider reasoning defaults are retained.
A token limit is not a dollar spending cap. Use confirmed available promotional
credits; no cash purchase or paid continuation is authorized. Errors stop the run.
The provider's Stop preference is already confirmed saved.

Results report exact model IDs, test choice, prediction correctness, numerical
grounding, scope limits, usage and elapsed time. A single constructed case does
not select the best general research model. Truncation is labeled a generation
budget issue, not an incorrect scientific answer. No final model is selected
automatically. Partial attempts are retained under `artifacts/runs/model-comparison/`.

Files used for this step:

- `counterlab/investigator.py`: bounded model/tool loop and evidence validation.
- `scripts/compare_nemotron.py`: offline preview and explicit live comparison.
- `tests/test_investigator.py`: mock-response tests; no credentials or network.

All 24 tests and the revised offline preview passed October 24. The assistant made
no new live inference calls. Future results preserve finish reasons and response
metadata without storing raw reasoning. The API contract follows Nebius's
[tools](https://docs.tokenfactory.nebius.com/ai-models-inference/function-calling)
and [structured JSON](https://docs.tokenfactory.nebius.com/ai-models-inference/json)
documentation. Ultra's tool/structured-answer integration passed in the user's
run; Super VL's tool integration remains unverified because generation truncated.

### VS Code environment notice

Calling `.venv\Scripts\python.exe` directly selects the correct Python environment;
the terminal does not need an activation label. Our inference scripts read the
project `.env` themselves. VS Code's optional terminal environment injection can
remain disabled; no editor setting or execution-policy change is required.

## Completed baseline check

From PowerShell in `C:\MY_PROJECTS\NVIDIAxNEBIUS`:

```powershell
.\.venv\Scripts\python.exe scripts\check_experiment_engine.py
```

Expected status: `experiment_engine_check_passed`. This uses the Python standard
library, makes no network/model requests, and reads no API credentials. It checks:

- Hand-worked cache-miss counts.
- Offline MIN against a separate exhaustive search over 3,279 tiny input/capacity
  combinations, with LRU as another baseline.
- Identical numerical replays on two explicitly generated traces.
- A saved protocol/input record and hashes linking the observations to it.

Evidence is saved under `artifacts/runs/engine-check/<protocol hash>/`. Existing
artifacts are preserved; conflicting contents cause an error. These generated
files are ignored by Git until deliberately reviewed for publication.

Boundary validation tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Completed controlled protocol comparison

The user has passed the reference milestone and independently repeated this
comparison with matching hashes. Its command is retained for reproduction:

```powershell
.\.venv\Scripts\python.exe scripts\run_protocol_comparison.py
```

Expected status: `protocol_comparison_completed`, with `controls_passed` and
`identical_event_replays` true. This default run is offline, reads no credentials,
and makes no inference requests. It verifies four cached source files against
pinned hashes, saves the experiment plan, and changes only the timing of the
budget gate's history refresh in our own implementation.

Observed locally: the constructed witness earns one gate credit under miss-based
history and zero under request-based history; miss counts are 19 versus 18.
All-fit controls both have 4 misses, and perfect-advice controls both have 28
(equal to offline MIN). A smaller miss count on this one constructed trace does
not establish general superiority. The timing difference affects behavior; the
reports' full disagreement and the paper's theorem remain unresolved.

Missing cached sources on another computer can be retrieved explicitly with
`--fetch-sources`. That downloads four pinned public text files, checks hashes,
and never imports or executes downloaded code. Hash mismatches preserve existing
files and stop the run. External source bytes stay under ignored `downloads/`.

New files: `cases/paging/sources.json` records source versions; the
[source audit](cases/paging/SOURCE_AUDIT.md) explains differences;
`counterlab/protocol_variants.py` isolates the timing change;
`scripts/run_protocol_comparison.py` runs and records it; and
`tests/test_protocol_comparison.py` checks control of random draws and layers.
The current complete test suite has 15 tests, all passed locally.

## Completed milestone: paper-linked reference

The following commands are retained for reproduction; this milestone is complete:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts\check_paper_reference.py
```

At this milestone 13 tests passed, followed by `paper_reference_check_passed`. The check
compares layer constraints with independently enumerated prefix-optimal caches
(18,045 comparisons), checks perfect advice on 4,368 finite cases, and saves 12
reference runs plus matching event replays. It uses no inference credits and
requires no new packages.

New files and their purposes:

- [counterlab/learning_paging.py](counterlab/learning_paging.py): layer state,
  online priority baseline, and prediction-budget eviction reference.
- [tests/test_learning_paging.py](tests/test_learning_paging.py): checks budget,
  gate history, eviction priorities, seeded replay, and invalid inputs.
- [scripts/check_paper_reference.py](scripts/check_paper_reference.py): independent
  finite verification and saved event evidence.
- [cases/paging/README.md](cases/paging/README.md): source locations, declared
  implementation choices, and remaining source/protocol parity requirements.

The reference uses exact layers without forgiveness, and does not claim the
paper's optimized runtime or benchmark reproduction. Gate timing is explicitly
recorded and still needs external implementation parity. The real-disagreement
gate G1 remains open. Final Nemotron selection comes after faithful investigation
inputs are available.

## Experimental scope

The baseline contract uses an empty initial cache, one unit of cost per miss,
mandatory insertion on a miss, and identical inputs/capacity across policies.
LRU evicts the least recently used resident. Offline MIN evicts the resident
whose next request is furthest in the future; it has oracle access to the trace
and is not a deployable online competitor.

The independent tiny-case verifier searches every legal eviction choice. This is
a numerical correctness check, not a proof of the paper's robustness theorem.
Worker/container isolation has not yet been implemented; run only the reviewed
local code in this repository.

## Research implementation gate

The selected source is [Towards Optimal Robustness in Learning-Augmented Paging](https://proceedings.mlr.press/v306/chen26gt.html).
Its [official code link](https://github.com/Natureal/ICML-Cache-Coliseum) is available
for inspection; reuse rights have not been established here, and no external
implementation was copied into the baseline engine.

Before calling the case a research reproduction, establish external algorithm
and protocol parity, prediction corruption, request generators, initialization,
and metric/denominator choices. Independent finite checks of our reference pass;
external fidelity remains unresolved. Finite curves cannot settle the paper's
asymptotic claim. Then compare Ultra and Super VL on actual investigation tasks.

## Credentials and spending

Keep the Nebius key only in local `.env` or backend deployment secrets; `.env` is
ignored. Never place credentials in frontend variables, logs, or exported evidence.
The user has confirmed saving the provider's Stop-usage-at-trial-end preference.
Only confirmed promotional credits are the current planning budget. Both grants
are redeemed; the user's October 24 screenshot confirms $50 account balance and
$0.99 separate trial credit. Do not put private redemption codes in this repository.
The emailed partner offers are separate claims, not Token Factory balance.
Deployment access and costs remain to be resolved.

## Planning

- [PRD](COUNTERLAB_PRD.md)
- [Setup](COUNTERLAB_SETUP.md)
- [Readiness tracker](READINESS_TRACKER.md)
- [Delivery and evaluation](COUNTERLAB_DELIVERY_PLAN.md)

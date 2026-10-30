# Inspect CounterLab without a key

This is a **recorded evidence build** of CounterLab. It starts no inference,
Docker worker or paid service. Python 3.13 is recommended; no packages are needed.

## Open the portable build

1. Extract the complete `counterlab-judge.zip` into a new folder.
2. In that folder run `python serve.py` (Windows: `py -3.13 serve.py`).
3. Open **http://127.0.0.1:8002/**. Keep the terminal open while inspecting.

`python serve.py --verify-only` checks every packaged file against the manifest.
If port 8002 is busy, use `python serve.py --port 8003`. Do not open `index.html`
directly: browsers need HTTP to load and verify the JSON records.

## Five-minute inspection

| Where | What to inspect |
| --- | --- |
| Home (first screen) | The product: setup checklist, numbers, recent investigations, examples and a drop zone to start. |
| Investigations → an investigation | Recorded open investigations (the first was planned live by Nemotron on October 30; the others are labelled simulated planning): progress rail; tabs for the overview, each experiment (claim, committed explanations and bet, charts with every seed, verdicts, code-written finding, harness code), inputs, activity (every request and retry) and the sealed record with the replay package. The live record is labelled Nebius/Nemotron; the three simulated examples are labelled separately. New live runs require the source build. |
| New investigation and Settings | Shown in the hosted demo for orientation; starting, saving a key and building the sandbox need the local app. |
| Case study → Sources → Claim audit | Five bounded questions, exact record-field citations, comparability checks and unresolved coverage. Save its JSON and recheck it with the full source build. |
| Case study → Guided demonstration | A real recorded Nemotron success, a wrong prediction, then every policy's aggregate result. |
| Case study → Research study → Design an experiment | Prepare a bounded human-designed plan and export its checked offline runner; this browser edition does not execute the new plan. |
| Case study → Evidence → Evidence library | Eight replay packages, explicit evidence types and setup, checksum-checked saving and replay commands. |
| Case study → Evaluation → Fresh source evaluation | Eight frozen tasks, all options, failures and zero-inference baselines. |
| Case study → Research study → Source investigator | Latest prediction guard, clearly labeled **simulated planning** with real isolated numerical executions. |
| Case study → Research study → Source reproduction | One selected supporting reproduction slice and its limits. |
| Case study → Evidence / downloads | Plans, observations, hashes and portable replay instructions. |

The browser verifies snapshot JSON bytes. Numerical checks ran at packaging;
they do not rerun in this browser. For independent local recomputation, download
a replay ZIP, extract it into another folder and follow its `README.txt`.
The case-study guarded investigation and evaluation replays need only standard-library
Python; they do not regenerate model replies. For an **Open Lab** download,
`python replay.py` checks hashes and recomputes findings from the saved measurements.
The optional `--rerun` executes the included harness and code locally, needs their
imported packages, and does not itself provide Docker isolation. Review that code
before rerunning it, or use a separate container. The long source-slice replay first
needs an explicit `python fetch_reference.py --download` (or `--local-file PATH`)
to install the pinned upstream file, which is not bundled. That setup checks its
SHA-256; subsequent replay is offline and can take a few minutes. Hashes are
consistency checks, not authorship proof.

In the evidence library, choose **Check package** before **Save checked ZIP**.
The browser checks size, ZIP signature and SHA-256 against this portable release's
manifest. It refuses a mismatched or incomplete file. A session file-check
receipt is available; numerical replay still requires the package's Python
command. Other views retain their direct download links.

## Live workflow and required tools

The design workbench needs no model credits. In this portable edition, save its
plan and runner into a new folder, then use Python 3.13:

```powershell
python counterlab-experiment.pyz counterlab-plan.json --output counterlab-result.json
python counterlab-experiment.pyz counterlab-result.json --verify
```

The full local app also offers the same bounded in-memory Python calculation.
It starts no model or Docker worker. Human experiments are not added to the
frozen benchmark; export results before leaving the workbench view.

Use the evidence interface's **Download source & live workflow** link for the
full source build. It contains the FastAPI app and explicit-consent
Nebius workflow. Nemotron proposes experiments and precommits predictions;
local restricted Docker workers measure admitted tests; deterministic code
builds the factual report. Nebius Token Factory supplies the runtime inference.
The static build is a companion to that working implementation, not fresh AI.

No planning advantage over the contract heuristic has been established in the
frozen paging evaluation. The case-study prediction guard has integration evidence
but no new live-model benchmark. Open Lab also accepts supported paper and code
uploads for bounded Python/CPU experiments. Its recorded live Nemotron run
establishes one working end-to-end example; broader design quality is unmeasured.
Neither workflow resolves a theorem or the full published research disagreement.

## Full source setup

Extract `counterlab-source.zip`. From its root:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe scripts\start_app.py --read-only --port 8001
```

Open **http://127.0.0.1:8001/** for Home and the recorded Open Lab investigations.
Use **Case study** for the earlier paging evidence. The compiled normal UI is included;
Node and Docker are unnecessary for recorded inspection. The source-reproduction
view can inspect its frozen three-row comparison without the optional full
reference, and explicitly labels the unavailable full-artifact identity check.
For that additional check run `python scripts/fetch_reference.py --download`.
Installation downloads
the pinned dependencies. Runtime read-only inspection does not need a network.
See `APP_GUIDE.md` / `COUNTERLAB_SETUP.md` for the separate live configuration.
Never place an inference key in frontend code. A new live run requires explicit
credit-use consent and a configured local Docker worker.

## Judging access window

The [official rules](https://nebiusglobalaihackathon.devpost.com/rules), checked
October 30, specify judging December 9–23, 2026. Keep the working build freely
accessible through **December 23 at noon Pacific**. Public URLs must be verified
after deployment; this guide alone is not proof of public access.

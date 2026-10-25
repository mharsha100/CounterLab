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
| Guided demonstration | A real recorded Nemotron success, a wrong prediction, then every policy's aggregate result. |
| Evaluation → Fresh source evaluation | Eight frozen tasks, all options, failures and zero-inference baselines. |
| Research study → Source investigator | Latest prediction guard, clearly labeled **simulated planning** with real isolated numerical executions. |
| Research study → Source reproduction | One selected supporting reproduction slice and its limits. |
| Evidence / downloads | Plans, observations, hashes and portable replay instructions. |

The browser verifies snapshot JSON bytes. Numerical checks ran at packaging;
they do not rerun in this browser. For independent local recomputation, download
a replay ZIP, extract it into another folder and follow its `README.txt`.
The guarded investigation and evaluation replays need only standard-library
Python; they do not regenerate model replies. The long source-slice replay first
needs an explicit `python fetch_reference.py --download` (or `--local-file PATH`)
to install the pinned upstream file, which is not bundled. That setup checks its
SHA-256; subsequent replay is offline and can take a few minutes. Hashes are
consistency checks, not authorship proof.

## Live workflow and required tools

Use the evidence interface's **Download source & live workflow** link for the
full source build. It contains the FastAPI app and explicit-consent
Nebius workflow. Nemotron proposes experiments and precommits predictions;
local restricted Docker workers measure admitted tests; deterministic code
builds the factual report. Nebius Token Factory supplies the runtime inference.
The static build is a companion to that working implementation, not fresh AI.

No advantage over the contract heuristic has been established. The latest
guarded workflow has integration evidence but no live model evaluation. This
prototype covers one reviewed paging adapter, not arbitrary papers or uploaded
code, and resolves neither a theorem nor the complete research disagreement.

## Full source setup

Extract `counterlab-source.zip`. From its root:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe scripts\start_app.py --read-only --port 8001
```

Open **http://127.0.0.1:8001/?view=demo**. The compiled normal UI is included;
Node and Docker are unnecessary for recorded inspection. The source-reproduction
view can inspect its frozen three-row comparison without the optional full
reference, and explicitly labels the unavailable full-artifact identity check.
For that additional check run `python scripts/fetch_reference.py --download`.
Installation downloads
the pinned dependencies. Runtime read-only inspection does not need a network.
See `APP_GUIDE.md` / `COUNTERLAB_SETUP.md` for the separate live configuration.
Never place an inference key in frontend code. A new live run requires explicit
credit-use consent and a configured local Docker worker.

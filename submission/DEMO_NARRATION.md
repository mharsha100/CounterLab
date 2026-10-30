# CounterLab — timed demo narration

Private local review cut created October 26, 2026. Measured planned timeline: **160.708 seconds (about 2:41)**.

**Draft status:** edited still-frame walkthrough of the working interface, with a clearly labeled synthetic guide voice. It is not a continuous screencast, the entrant’s own narration, a public upload or a completed submission.

The numerical examples are bound to the reviewed source/evidence release. All underlying results retain their original scope. No fresh model calls are made.

Local assets are under `artifacts/demo/20261026-review/`: `counterlab-demo-review.mp4`, `captions.srt`, `narration.txt`, `chapters.txt`, the source captures, timing manifest and fresh replay result. Private media assets are excluded from the source release.

## Recommended final recording (pitch + working product, about 2:50)

Updated October 28, 2026 for the product UI. Judges may score from the video alone, so show **one
live investigation with Nemotron on Token Factory**. Rehearse with `scripts/preview_open_lab.py` (no
credits), then record against the real app (`scripts/start_app.py`; key saved in Settings; Docker
Desktop running). A live run makes three to five Nemotron requests. Speed up waiting time and label it.

Updated October 30: the cache example ran live end to end in 87 seconds (3 requests). Use it for the
recording; describe whatever your run shows. If you cannot record a new run, the recorded live run
(first row in Investigations) shows the same screens: Nemotron's first bet failed, its follow-up
harness crashed in the sandbox and was repaired from the traceback, and the follow-up bet held.

| Time | Screen | Say (in your own words) |
| --- | --- | --- |
| 0:00–0:15 | Home | "In Hugging Face's ICML 2026 reproduction effort, independent teams reached opposite verdicts on the same claims for 242 papers. An AI explanation won't settle that. An experiment can. This is CounterLab." |
| 0:15–0:30 | Settings: connection shows *Connected*, test request passed, sandbox *Ready* | "It runs on your machine. Paste a Nebius key, CounterLab confirms NVIDIA Nemotron 3 Ultra is available, and builds a sealed sandbox." |
| 0:30–0:45 | New investigation: pick the cache-eviction example (or drop a paper and two implementations), type the question, approve | "Bring a paper, the code, or two implementations that disagree, and ask what you want settled." |
| 0:45–1:15 | **Live:** the progress rail moves; open Experiment 1 when committed | "Nemotron reads both, picks a testable claim, names competing explanations and what each predicts, and commits its bet. The plan is hashed before anything runs." |
| 1:15–1:35 | Rail at *Check* → *Run twice*; Activity tab | "A deterministic guard checks the plan, then the code runs in a Docker sandbox with no network, twice, with the same seeds. If Nebius hiccups, CounterLab retries with backoff, and you can see it here." |
| 1:35–2:00 | Experiment 1 charts, verdict table, finding | "Every number is written by code from the measurements, not by the model. Here Nemotron's bet failed, and CounterLab says so." (Use your run's actual result.) |
| 2:00–2:15 | Experiment 2 → *Checks and repairs*; Activity tab; Investigations list | "Then Nemotron designs a follow-up from the measured results. When its harness crashed in the sandbox, CounterLab sent back the traceback and Nemotron fixed it. Every investigation is sealed and searchable." |
| 2:15–2:30 | Case study → Evaluation | "We also measured whether the AI helps, in a deep case study: it found the differences, but so did a simple heuristic, and we show that." |
| 2:30–2:50 | Record tab → Download replay package; terminal `python replay.py` | "Everything downloads as a sealed package that rechecks offline with plain Python. CounterLab, on Nebius Token Factory and NVIDIA Nemotron." |

Recording checklist: 1080p or higher, browser zoom 110–125%, notifications off, never show the
key field with a key in it, `.env`, terminal history or account pages; English captions; final length
checked under 3:00. If a live run stops for review, that is fine to show: the reason and the next step
are on screen.

The earlier timed draft below remains the private review cut of the case study.

## 0:00–0:14 · A test worth trusting.

**Screen:** Recorded interface.

When research implementations disagree, another explanation is not enough. We need an experiment that separates them, a prediction committed before execution, and evidence someone else can replay. This is CounterLab.

## 0:14–0:29 · Compare the contracts first.

**Screen:** Pinned source inspection.

Start by checking what is comparable. Here, inspected implementations differ in history updates, random priorities, forecast delivery, and miss counting. CounterLab makes those differences explicit before drawing a conclusion.

## 0:29–0:45 · An AI proposer. Measured evidence.

**Screen:** Saved workflow · no fresh inference.

The Python application uses NVIDIA Nemotron through Nebius Token Factory to propose tests and predictions. Restricted local workers measure admitted experiments. Deterministic code builds the factual report. This walkthrough inspects saved model responses.

## 0:45–1:05 · One changed rule. A measured difference.

**Screen:** Real recorded Nemotron plan.

In this recorded Nemotron example, only history timing changes. Requests, forecasts and randomness stay fixed. The model predicts a difference. Measurements show five hundred and nine versus five hundred and ten misses, and zero versus ten gate credits. The result is finite and reproducible.

## 1:05–1:19 · Keep the failure visible.

**Screen:** Real recorded Nemotron prediction.

The model can also be wrong. On this smaller cache, it predicts both counts will differ. Both have six hundred and thirty six misses and zero gate credits. The failed prediction stays in the evidence.

## 1:19–1:34 · Check before executing.

**Screen:** Simulated planning · real numerical execution.

The newer workflow checks necessary conditions before execution, then returns a rejection reason for a follow-up. This guard example uses simulated planning with real numerical execution. Its live model improvement has not been measured.

## 1:34–1:51 · Evaluate the AI, too.

**Screen:** Frozen real-model evaluation.

Across eight frozen development tasks, adaptive Nemotron finds both available differences. So does the zero-inference heuristic. Wrong predictions and truncated responses remain visible. We have not established an advantage over that baseline or a general model ranking.

## 1:51–2:06 · Design a new bounded test.

**Screen:** Human-designed synthetic diagnostic.

You can also edit synthetic inputs, commit predictions or abstain, then compare both rules without model credits. This workbench keeps new experiments separate from the frozen model evaluation. Every result retains its original settings.

## 2:06–2:24 · Take the evidence with you.

**Screen:** Completed fresh-process replay.

A downloaded replay recomputes twenty two paired tests and independently checks forty five profiles. This is the actual completed result. It needs standard-library Python, with no model key, Docker or inference credits. The evidence can be checked outside the app.

## 2:24–2:40 · Commit. Check. Measure. Replay.

**Screen:** Private review draft.

CounterLab currently supports one reviewed paging adapter. The full research disagreement remains open. What it delivers is an inspectable investigation: explicit contracts, committed predictions, preserved failures, bounded experiments, and evidence you can replay.

## Final recording and publication

Use this cut to rehearse, review the claims and record a continuous screencast with the chosen final narration. Keep saved-model and simulated-planning labels visible, retain the failed prediction and every policy row, and show the actual completed replay. Recheck the final encoded duration after edits.

Public source, accessible test-build links and public YouTube upload remain pending. Keep the repository and this draft private until a later explicit publication instruction. Do not display account menus, API keys, promo codes or private terminals.

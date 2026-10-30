# CounterLab — submission desk

Prepared October 26, 2026. **Local preparation only; not a submitted entry.**
Use this page to assemble the entry without mixing private rehearsal materials,
recorded model results and new simulated integration checks.

## Copy and attachments

| Entry item | Use | Readiness |
| --- | --- | --- |
| Project name | CounterLab | Ready |
| Tagline | Turn research disagreement into experiments you can replay. | Ready |
| Track | Best Apps and Agents | Proposed; final entry selection pending |
| Description | [DEVPOST_DRAFT.md](DEVPOST_DRAFT.md) | Draft prepared; final working links pending |
| Sponsor feedback | [TOOL_FEEDBACK.md](TOOL_FEEDBACK.md) | Prepared from actual use; no invented feedback for unused services |
| Technical access instructions | [JUDGE_GUIDE.md](JUDGE_GUIDE.md) | Prepared; public access test pending |
| Narration and shot plan | [DEMO_NARRATION.md](DEMO_NARRATION.md) | Prepared; final functioning-app recording pending |
| Source | https://github.com/mharsha100/CounterLab | Verified private upload; not publicly accessible |
| Working build URL | Not yet published | Must be supplied after access verification |
| Video URL | Not yet uploaded | Must be supplied after playback verification |
| Gallery images | `submission/gallery/` (ten 2400×1600 PNGs, 3:2) with the captions below | Ready; 01 and 03–07 recaptured October 30 from the first live Nemotron investigation |

Do not paste this readiness table or unresolved placeholders into the final entry.
The source commit verified on October 26 is
`a9fe693cbc979c33097b824b8a6049c34788bd40`. The later final quality review changes
application code and documents; its new frozen archive needs a private update
before source publication. The earlier archive remains unchanged.

## Claims that must remain distinct

| Claim | Evidence and wording boundary |
| --- | --- |
| Any paper or code can be investigated | The open workflow (upload → Nemotron design and commitment → guard → Docker sandbox, run twice → code-written report → follow-up → sealed replay) is implemented, tested end to end with simulated planning and the real sandbox, and was run live once on October 30 (Nemotron 3 Ultra, 3 requests, 87 s, including a harness crash Nemotron repaired from the traceback). One live run shows the workflow works; it does not measure Nemotron's open-design quality. The other three recorded open examples are labelled simulated planning. |
| Nemotron selected experiments through Nebius | Real saved provider responses and the runtime backend establish use. Say **NVIDIA Nemotron through Nebius Token Factory** aloud in the video. Opening the static site does not issue a model request. |
| A measured difference can be replayed | Show the recorded 509-versus-510 example and its downloadable numerical replay. This is a finite case, not proof of a general theorem. |
| Failed predictions remain inspectable | Show the recorded 636-versus-636 example with the original prediction visible. Do not remove failed runs from the evaluation narrative. |
| The evaluation includes non-AI baselines | Display all four policy rows in DEVPOST_DRAFT. The heuristic found both available differences too; no model selection advantage is established. |
| A new guard rejects contradictory predictions | Label the later demonstration **simulated planning, actual numerical execution**. Live model improvement has not been measured. |
| The release installs and replays | Acceptance receipt and logs verify the frozen package. Passing software checks does not establish scientific validity or external user usefulness. |

## Gallery images

Captured from the product UI with headless Chromium at 1500×1000 and 1.6× scale (2400×1600 PNGs,
3:2): 02 and 08–10 on October 28, 2026; 01 and 03–07 on October 30 after the first live Nemotron
investigation (`f37f1506613e4c78b194a93265caa0e7`, promoted into the recorded examples so the
hosted edition shows it). No account panels, keys, notifications or private paths appear. Upload in
this order; the first is the Devpost thumbnail.

Images 03–06 show that live run: Nemotron 3 Ultra on Nebius Token Factory wrote every plan, bet and
harness; CounterLab ran, checked and reported. The other recorded examples visible in 01 and 07
are labelled simulated planning on screen.

| File | Caption |
| --- | --- |
| `01-home.png` | CounterLab: put a research claim to the test. Drop a paper or code, or start from an example; the latest investigation was planned live by Nemotron. |
| `02-new-investigation.png` | One form: the question, the paper and code (or links), and a bounded credit approval. Nemotron and sandbox readiness are checked before you start. |
| `03-live-run-activity.png` | A live Nemotron run, end to end in 87 seconds: three requests, every token and timing logged. The third request repaired a harness that crashed in the sandbox. |
| `04-investigation-result.png` | Nemotron's first bet failed; its follow-up held. Which explanations survived is written by code from the measurements, not by the model. |
| `05-committed-before-running.png` | Nemotron's competing explanations, what each predicts, and its bet are hashed before anything runs. |
| `06-measured-twice.png` | Every seed, run twice in a sealed Docker sandbox with no network; the repeat matched exactly. Each prediction is judged with the seeds that agree and a sign test. |
| `07-investigations.png` | Every investigation, sealed and searchable, with status, committed bets and requests used; simulated examples are labelled. |
| `08-settings-connection.png` | Connect NVIDIA Nemotron on Nebius Token Factory: save the key, check the catalog, send a test request; build the sandbox. |
| `09-case-study.png` | Case study: a real ICML 2026 disagreement in learning-augmented paging, investigated end to end with a frozen AI-vs-baseline evaluation. |
| `10-offline-replay.png` | The downloaded evaluation package replays offline with standard-library Python: no key, Docker or credits. |

The earlier gallery sets are superseded.

## Release identity

The current local release is `artifacts/releases/product-final-20261030/` (product UI,
connection hardening and the first live Nemotron investigation); its `release-summary.json`
records the source and judge ZIP hashes. The earlier quality-reviewed release is
`artifacts/releases/counterlab-final-review-20261026/`. Its `release-summary.json` records the exact source and judge ZIP hashes;
its `acceptance-receipt.json` records the final package checks. Do not substitute
an older archive with a similar filename.

The preceding private GitHub upload used these historical archives, retained
unchanged under `artifacts/releases/counterlab-project-freeze-20261026/`:

- `counterlab-source.zip`: SHA-256
  `73c3b6b0a933d24afc22c1069d13319335f19c70c39d6aecf8c6eaf36e109796`.
- `counterlab-judge.zip`: SHA-256
  `a025c539b2397e8f02c6b121420121a43f5697d93489807bdcd8b2aeb834aa60`.
- Historical acceptance: `acceptance-receipt.json` in that directory.
- Private upload: `artifacts/releases/counterlab-private-sync-20261026/github-sync-receipt.json`.

The quality-review source still needs a deliberate private repository update
before a later authorized public release. Do not describe the previous GitHub
commit as containing these newer changes.

The private review video is an edited-still rehearsal with synthetic narration.
It is not the final functioning-app recording or a public YouTube submission.

## Remaining gates

0. Done October 30: one open investigation ran live on the entrant's machine, was promoted
   (`cases/open_lab/recorded/f37f1506613e4c78b194a93265caa0e7`), the evidence edition was
   rebuilt and gallery images 01 and 03–07 were recaptured from it.
1. Obtain the user's explicit authorization before making the source/site public;
   the current instruction is to keep the repository private.
2. Verify public source, build, downloads and setup without login or payment.
3. Finish and verify the under-three-minute English demonstration video.
4. Insert verified links, and review ownership, notices
   and AI-assisted solo-development disclosure with the entrant.
5. Review and submit the final entry, then retain access through judging.

These are actions within the existing five submission steps, not new countdown
steps. Description preparation alone does not complete the materials step.

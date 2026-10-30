# Local release validation — October 30, 2026

## First live Nemotron investigation (October 30)

Run on the entrant's Windows machine with the product app (`scripts/start_app.py`), after the
entrant saved the key in Settings, checked the connection (the catalog lists
`nvidia/Nemotron-3-Ultra-550b-a55b`), sent the test request and built the sandbox with the Settings
button on Windows Docker Desktop.

- **Run `f37f1506613e4c78b194a93265caa0e7`** (cache-eviction example, 16,384-token allowance,
  follow-up on): completed in **87 s** with **3 Nemotron requests** (experiment 1 design 20.6 s,
  experiment 2 design 20.6 s, experiment 2 repair 4.2 s) and **23,005 tokens** (9,348 prompt,
  13,657 output of which 10,122 reasoning). Token Factory accepted the strict JSON schema (no
  fallback); no retries; the returned model matched the requested one; Docker sandbox, no network.
- **Experiment 1** (refresh policy): refresh on miss only 601.9 vs refresh on every request 557.3
  misses (10 seeds). Nemotron's bet (E1) and E2 failed (0/10 seeds); the repeat run matched exactly.
- **Experiment 2** (follow-up, policy × prediction noise): Nemotron's first harness crashed on all 40
  measurements (`ValueError` parsing its own condition names). CounterLab returned the traceback;
  the repaired harness ran, the repeat matched exactly, and the bet (E1) held on 10/10 seeds for both
  comparisons (780 vs 802 with perfect predictions, 780.8 vs 802 with noisy ones); E2 and E3 were
  contradicted.
- The record verified, was promoted into `cases/open_lab/recorded/`, and all **293 Python tests** (295 after fix 6)
  and **25 frontend tests** pass with it included; both builds and the evidence edition were rebuilt.
  Its downloaded replay package re-verifies 18 files, recomputes both findings and re-executes both
  experiments offline (`replay.py --rerun`). The hosted edition lists it first and opens it.

Fixed from what this run exposed:

1. The investigation overview showed only the first sentence of each experiment's finding, so
   explanation E2 read as *held* beside its *contradicted* badge. The overview now shows every
   comparison and the consistent/contradicted line.
2. Once a live run existed, Home credited the simulated examples' bets and requests to Nemotron
   (6/8 bets, 10 requests). Only Nemotron-planned runs are counted now (1/2, 3).
3. In the entrant's browser, *Start investigation* gave no visible response (not reproduced; the
   same form started the run from another browser). The form now reports any problem beside the
   button and scrolls to the field that needs it, so a click can never look like nothing happened.
4. README and Devpost text no longer state the simulated-planning cache finding (refreshing hurts
   with noisy predictions), which Nemotron's live follow-up did not reproduce.
5. After promotion, the entrant's own run was listed as a bundled *Recorded* example in their own
   workspace, so the setup checklist still said to run a first investigation. A promoted run now
   stays listed as yours where you ran it (new test); other installs see it as recorded.

6. A second live run that morning (`8a57c696…`, 4 requests, 48,803 tokens, 146 s) showed two more
   issues. Nemotron's follow-up design hit its output allowance, and the single re-ask used up the
   one redesign, so a draft with a malformed prediction was committed, rejected by the guard, and
   shown only as *Not measured*. A truncated reply no longer uses up the redesign (up to three design
   requests per experiment, within the seven-request cap), and an unmeasured experiment now states
   why on the overview and experiment tab (for older records too). Two new tests; **295 Python
   tests** pass. That run's first experiment is valid as recorded: both implementations measured
   1,337.1 misses, so both of Nemotron's predicted differences failed.

Still not verified: Nemotron's open-design quality beyond this one run, live link downloads, and
Stop during a sandbox run on Windows Docker Desktop.


## Product interface and connection hardening (October 28)

Scope: the app is now organised as a product (Home, New investigation, Investigations, an
investigation page with tabs, Settings, the case study as a secondary section) and the Nemotron
connection is hardened. Guidance applied: Vercel's Web Interface Guidelines, the UI UX Pro Max
pre-delivery checklist, Linear-style app-shell patterns and SaaS sidebar navigation rules; the
retry policy follows the official OpenAI SDK. **No Nebius requests were made** (Token Factory is
unreachable from the build environment); live behaviour was exercised against a local fake
Token Factory server and the simulated planner.

- **292 Python tests passed** (80 s, no skips with Docker running). New: a local OpenAI-compatible
  fake server injects HTTP 429 with `Retry-After`, 503, 401/402/403/404, dropped connections, slow
  responses (timeouts) and schema rejections; the client retries what is temporary (at most three
  retries, backoff with jitter, `Retry-After` honoured, one retry after a timeout), stops at once on
  what is not, falls back from strict to relaxed schema to JSON mode, and records every event.
  Service tests cover saving a key (never echoed, other `.env` lines kept, injection rejected,
  read-only refused), the free catalog check and the paid test request, a run that survives two
  503s and records them, fallback to the strongest available Nemotron model, Stop during a model
  request (state *Stopped* within 3 s, record sealed), Stop during a sandbox process, Run again with
  verified inputs, removing a run from the list, and a clear message when Docker is missing.
- **25 frontend tests passed** (routes and deep-linked parameters, failure wording, chart helpers).
  Both production builds pass; fonts are self-hosted (IBM Plex, SIL OFL 1.1).
- **Browser walkthrough of the product** (Playwright/Chromium, preview server: simulated planning,
  real Docker sandbox): Home → N opens the composer → example → missing consent explained beside the
  field with focus moved → start → live progress rail → completed → Experiment tab deep-linked →
  Activity → replay package downloaded → Run again reuses inputs → Stop → *Stopped* → status filter
  and search (with `/`) in the URL → Settings rejects a malformed key, saves a valid one without ever
  showing it, checks the connection and sends a test request → Ctrl K palette starts an example. No
  console errors.
- **Hosted evidence edition** (served from a GitHub-Pages-style subpath): hosted-demo labels, start
  disabled with an explanation, three recorded investigations listed and opened, replay package
  downloaded from the verified snapshot, no write requests. The case-study walkthrough passes on
  the read-only app and the hosted edition.
- **Accessibility:** axe-core (WCAG 2.0/2.1/2.2 A/AA + best practice) found no violations in 23
  views and tabs (Home, composer, composer with an example, Investigations, an investigation's five
  tabs, Settings and all 13 case-study views) at 1440 px and 390 px; no horizontal scrolling at 390 px.
- **Not yet verified (October 28):** live Nemotron behaviour (design quality, timing, whether Token
  Factory accepts the strict schema or needs the fallback), the sandbox build button on Windows Docker
  Desktop, and live link downloads. *October 30: the first three are now covered by one live run
  (above); design quality across tasks and link downloads remain open.*

## Open investigations (October 27, late)

Scope: the new any-paper-or-code workflow (`counterlab/open_lab/`, the **New
investigation** screen, `scripts/setup_open_runner.py`, `preview_open_lab.py`,
`promote_open_run.py`, `cases/open_lab/`). Case-study records, frozen protocols
and the paging worker are unchanged. **No Nebius requests were made**: the build
environment could not reach Token Factory, so every design below is simulated
planning written by the developers and labelled as such in the app and records.

- **271 Python tests passed**, 26 of them new for open investigations:
  intake (archive path normalisation, symlink and size limits, PDF text, link
  allowlist), guard (non-discriminating designs, forbidden modules/calls/attrs,
  helper aliases, harness must load the uploaded code), workflow (commit before
  run, redesign before commitment, harness repair with predictions locked,
  a truncated design re-asked once with a doubled allowance, malformed
  designs stopped after one re-ask with nothing run, HTTP 429 never retried, returned-model mismatch
  stops the run), report statistics and sign test, sealing, tamper detection,
  `replay.py --rerun`, API origin/consent checks, and a real Docker sandbox run
  (no network, read-only root, non-root user). **24 frontend tests
  passed**, including open-investigation failure wording, axis ticks and label
  wrapping. Both production builds pass.
- **Sandbox image:** `python:3.13.5-slim` pinned by digest with numpy 2.5.3,
  scipy 1.18.1, pandas 3.0.6, scikit-learn 1.9.1 and networkx 3.7. After each
  build `setup_open_runner.py` probes the boundary: network connect fails, root
  filesystem is read-only, user is 65532, capabilities are empty. Runs use
  `--network=none --read-only --cap-drop=ALL --security-opt no-new-privileges`,
  2 GB memory, 2 CPUs, 128 processes, a 256 MB noexec `/tmp`, 240 s per run and
  30 s per measurement call. (In this environment the image was built from a
  local root filesystem because Docker Hub is unreachable; on a normal machine
  the script pulls the pinned digest.)
- **Three examples, end to end, real sandbox** (browser-driven through the UI,
  20–28 s each): reservoir samplers (first harness has a wrong path, the guard
  passes, the run fails, one repair succeeds; Group B first-k inclusion 0.8236×
  expected vs theory 0.808×; follow-up: bias grows as k/n shrinks), Welford
  (log10 relative error −8.39 vs +0.88 for the textbook formula at offset 1e9),
  cache eviction (the committed bet fails: 1,626 vs 1,692.8 misses; follow-up
  shows refresh-every-request gains 93 misses at noise 5 and loses 152.3 at
  noise 100). Every repeat matched exactly.
- **Downloaded replay packages** verified offline with standard-library Python;
  `--rerun` re-executed every experiment and reproduced every value; editing a
  measurement or finding makes the replay fail.
- **Real inputs:** a public GitHub repository ZIP (micrograd) and a text PDF went
  through intake, outline and prompt assembly within the size limits. Live
  GitHub/arXiv downloads could not be exercised here (blocked network); the
  fetcher is covered by tests with an injected transport.
- **Browser and accessibility:** read-only app walkthrough, evidence edition
  (recorded open investigations listed, start disabled with an explanation,
  replay ZIP downloads), axe-core WCAG 2.0/2.1/2.2 A/AA + best-practice with
  **no violations in all 14 views** at 1440 px and 390 px, and no horizontal
  scrolling at 390 px.
- **Not yet verified:** a live Nemotron open investigation (design quality,
  token use and timing), Docker Desktop on Windows for the open runner, and live
  link downloads. Run one example live before recording the video.

## Final submission polish (October 27)

Scope: interface wording and failure guidance, HTTP hardening, judge-facing
README, gallery images, Devpost copy and repository layout. **No model calls,
no Docker experiments, no paid services and no publication.** All 100 case files,
the worker and every frozen numerical/record module are byte-identical to the
October 26 release; only `counterlab/api.py` (security headers, credential-free
`/api/health`, provider status codes kept on the job) and
`counterlab/judge_release.py` (new docs paths) changed in the backend.

- **245 Python tests passed** (42.6 s), including three new security-header/
  health tests and a new rate-limit test: a planning request answered with HTTP
  429 makes one catalog read and one planning request, is sealed as
  `needs_review`, is never retried, and reports `provider_http_429` without the
  provider message or key. **21 frontend tests passed**, including three new
  wording tests. Both production builds pass; the setup check reports the
  interface build current.
- Browser end-to-end walkthrough (Playwright/Chromium) passed on the read-only
  local app, on the evidence edition served from a GitHub-Pages-style subpath
  (`/CounterLab/`) and on an app started from the freshly extracted source ZIP:
  guided tour, inline link to the failed prediction, trace explorer, recorded
  investigation, checked ZIP download, workbench comparison, Back/Forward and
  titles, with no console errors and no write requests.
- Writable-mode start flow checked with simulated planning and the in-process
  fixture worker (no Docker, no Nebius): consent gates the start button; a normal
  run shows the guard rejection and measured follow-up; a 429 run shows the
  actionable rate-limit message and never the raw code.
- axe-core 4.10 (WCAG 2.0/2.1/2.2 A and AA plus best-practice rules) found
  **no violations in any of the 13 views** at 1440 px and 390 px on the local app
  and at 1280 px and 390 px on the evidence edition. No view scrolls horizontally
  at 390 px. Security headers were confirmed on the extracted build; its read-only
  POST returned 403.
- Clean extraction: the new source ZIP installed into a fresh Python 3.13 venv
  from `requirements-lock.txt` (17 packages), passed the setup check and served
  the app; `serve.py --verify-only` verified all 35 judge-site files.
- The downloaded evaluation package replayed offline with standard-library Python
  3.13 in 2.7 s: 22 paired tests, 45 independent profiles, 145,041 events,
  16 + 16 runs rescored, 0 inference requests.
- Release built locally (not published):
  `artifacts/releases/final-check-20261027/`. Its `release-summary.json` records
  the exact source and judge ZIP hashes. Distribution checks passed with no
  credentials or full upstream artifact bundled.
- Live Nemotron behavior of the guarded v2 workflow is still unmeasured; the
  private GitHub commit is still the October 26 upload. **5 steps remain:
  0 project + 5 submission.**

## Final project quality review (October 26)

- **241 Python tests passed in 200.722 seconds; 18 frontend tests passed.** Both
  production builds pass. This is the final combined regression after the versioned
  source execution profile and Windows crash-test correction. The crash test exits
  the actual Python owner instead of its possible Windows launcher; all five
  ownership tests also passed three consecutive runs.
- Browser acceptance covered nested URLs, refresh, Back/Forward, headings and
  titles, keyboard skip navigation, checked-download status/focus, manual recovery
  from a failed source-record GET, and recovery from a render exception. The fault
  proxy recorded GET requests only. The source view fit a 390-pixel viewport.
- Real restricted Docker source execution passed with the new `source_wall60_v1`
  profile: one rejected synthetic prediction, one admitted experiment and two
  replays taking 30.187 and 28.884 seconds. The exported v3 package passed standalone
  replay. The earlier 15-second timeout failure remains retained; old v2 verifiers,
  receipts and frozen scientific code were not modified. No model call occurred.
- Fresh extraction of the candidate source passed in the earlier clean 17-package
  locked environment, with imports confirmed from the extraction. Its interface,
  source contract, historical guarded record/export and absent optional reference
  were checked with provider and credential access blocked. All three read-only
  start routes returned 403. Dependencies were unchanged, so no repeat install
  was required; the earlier clean-install evidence below remains applicable.
- Packaging checks verify 17 snapshot routes, all eight exports, source/member
  manifests, the whole portable site and distribution exclusions. All 100 case
  files remain byte-identical to the preceding freeze. The member contents of
  all eight replay ZIPs remain identical to the fully replayed earlier release.
- npm and OSV advisory queries returned no known matches for the locked packages.
  This is not a security certification. No speculative dependency changes were made.
- New release: `artifacts/releases/counterlab-final-review-20261026/`. Its
  `acceptance-receipt.json` records exact archives and verification evidence;
  detailed local logs are under `artifacts/freeze/20261026-final-review/`.
  Changes after extracted runtime acceptance are documentation and the separately
  regression-tested Windows process-exit test only.
- The user's port-8000 server was not replaced; restart it before adopting the
  updated live code. The private GitHub commit is still the previous release.
  Windows was tested locally; Unix locking and public hosting need their own
  environment checks. Live model quality, scientific generality and external-user
  usefulness were not re-evaluated. **5 steps remain: 0 project + 5 submission.**

## Previous clean installation and project freeze

- Extracted the previous reviewed source archive into a new folder, verified its
  source manifest, and created a fresh Python 3.13.5 virtual environment. Installed
  all 17 exact locked versions through isolated pip/PyPI configuration (cached
  wheels were available); `pip check` passed. This is a new environment on the
  same Windows machine, not a separate operating system or a clean-machine claim.
- Before installing optional reference data, the actual read-only launcher
  served HTML, workspace, source-reproduction, claim-audit, evidence-library and
  source-evaluation responses on port 8001. Missing full-reference verification
  was correctly reported. All three job-start routes returned 403. No `.env`
  existed in the extraction; no Docker or provider calls were required.
- A fresh `npm ci --ignore-scripts` installed 23 frontend packages. Both builds
  succeeded; all ten compiled/stamp files across the two editions are byte-for-byte
  equal to the reviewed workspace outputs. All eight download tests and four
  workbench tests passed in that fresh installation.
- The initial clean regression exposed five tests that loaded the diagnostic
  from ignored development history. Their setup now uses the same packaged,
  hash-checked protocol as the app. No runtime algorithm, model protocol or saved
  result changed. The full rerun passed **224 tests in 90.671 seconds**.
- All **eight extracted evidence packages** pass standalone Python with `-S`
  (third-party site packages disabled). This includes the retrospective prediction
  review, both evaluations, both source workflows, the original investigation,
  the 416-profile controlled study and the complete source slice. The source
  evaluation rechecks 22 paired tests, 45 independent profiles / 145,041 events
  and all 16 baseline / 16 model runs. The source slice reexecutes all ten seeds,
  30 profiles and 530 independent oracle profiles, matching the three selected
  reported aggregates. The original evaluation's receipt-only oracle coverage
  retains its documented limitation; replay does not regenerate model replies.
- The source slice's optional data was installed from the already-local file
  after its pinned SHA-256 passed. No reference download occurred. The restricted
  filesystem blocked its hard-link operation; the normal local process completed
  the same explicit installer. No isolation or algorithm policy was weakened.
- Current instructions now distinguish recorded inspection from developer-test
  fixture setup. `submission/PROJECT_FREEZE.md` defines the reviewed scope and
  the local frozen release path. Logs/receipts are under
  `artifacts/freeze/20261026/`, excluded from Git and distributable source.
- Zero new inference requests, paid services, credentials read or external
  publication. The user's port-8000 process remains untouched. The remaining
  five countdown items are submission work, not unfinished project acceptance.

## Workflow and interface acceptance

- Checked the four-step guided demonstration, recorded investigation, source
  audit, controlled study, source reproduction, both evaluations, source
  investigator, bounded workbench, run history and evidence library in a real
  browser. Reviewed mobile layouts at 390 px and desktop at 1280 px; wide tables
  scroll inside their containers. Dialog Escape restores focus. Empty history
  searches now show an explanation and a Clear filter action that restores focus.
- The all-fit study correctly displays eight undefined 0/0 ratios after warmup.
  The workbench's deliberately wrong predictions are contradicted by 4/4 misses
  and 0/0 credits; an invalid 513-request draft disables commitment. Downloaded
  plan, runner and result pass standalone numerical verification.
- All eight library ZIPs pass the actual browser checks. Deliberately corrupted
  bytes produce no save link; cancellation prepares no file. Workspace and
  catalog failures show errors and recover. The portable edition works below
  `/counterlab/`, exposes saved evidence and prepares workbench plans without
  live execution controls.
- Docker initially failed to start. Only its two validated temporary socket
  directories were renamed to recoverable backups; images, volumes and settings
  were retained. Details: `artifacts/ui/workflow-acceptance/docker-runtime-recovery.json`.
  The existing image/source fingerprints and actual isolation probe pass.
- The first fresh source run stopped without verified measurements and remains
  preserved as `needs_review`, with no retry. After recovery, a separately
  initiated simulated-planning run completed in 28.862 seconds: one repeat
  control and one history test, each executed twice in real containers. Its
  61,413-byte downloaded archive passes the standalone replay (two experiments,
  two measurement citations, one target measurement). The finite history result
  is 13,707/13,963 misses and 0/801 credits. This is integration verification,
  not a new model-quality evaluation. Frozen research/model records are unchanged.
- In-progress source responses now retain their workflow version, preventing
  the v2 UI from briefly displaying Historical v1. The queued-response regression
  verifies the version and unavailable export before execution.
- All 25 focused API/release tests and all 12 frontend checks passed. Following
  the label fix, the four guarded-source API tests passed again; both final
  production builds passed (38 inputs, four outputs each). A restricted-process
  test invocation stalled and was stopped; the successful offline run used the
  normal local process environment. No new test cases beyond the existing 224
  distinct Python tests are claimed.
- Evidence, logs, controls and screenshots are in
  `artifacts/ui/workflow-acceptance/`. Temporary previews use separate state;
  the user's port-8000 app is untouched. Zero real provider requests, credential
  reads, purchases or external publication. Fresh dependency installation and
  the final project freeze remain Step 3.

## Startup readiness

- The default setup diagnostic reads neither `.env` nor provider credentials,
  makes no network call, installs nothing and starts no Docker container.
  It checks Python 3.13, 17 locked packages, 38 interface inputs/four outputs and
  nine saved-manifest paths. Manifest presence is explicitly not verification
  of numerical contents. Provider readiness and credit balance stay unchecked.
- Both interface builds write source/output fingerprints. The Python verifier
  agrees with the actual Node-generated record. Same-size edits, added source,
  altered/missing assets, wrong editions, malformed records, unexpected paths
  and frontend credential files fail. Records are local consistency metadata,
  not independent signatures or a hermetic build guarantee.
- Actual stale-build rejection and current setup success are saved in
  `artifacts/ui/startup-stale-build-check.json` and `startup-readiness.json`.
  The optional read-only image inspection passed in `startup-readiness-worker.json`;
  unavailable Docker is separately tested and does not block inspection.
- Full regression: **223 Python tests passed in 151.799 seconds**. After adding
  one release-preflight test, **all nine focused release tests passed**. This
  covers 224 distinct Python tests across those runs. All **12 frontend checks**
  and both production builds pass. Release preflight rejects either stale
  edition before creating a destination or collecting evidence.
- The actual launcher served read-only workspace metadata, HTML, JavaScript,
  CSS and its build record using fresh state on port 8001, then was stopped.
  Receipt: `artifacts/ui/readiness-launcher-http.json`. The user's port 8000
  process was untouched. There were no provider calls, credential reads, worker
  executions, purchases or external publication for this milestone.
- Setup/startup is this countdown step's scope. Final workflow acceptance and a
  fresh dependency installation remain later project steps.

## Private video review cut

- Local MP4: 3,839,705 bytes, SHA-256
  `0874c6001283ff42bd066caad75525843378140e04271f05d1a9111ddd223c83`.
  Browser duration 160.709 seconds; 1920×1080, H.264, 24 fps, AAC guide narration,
  burned-in captions and an embedded English mov_text subtitle track.
- All **3,857 video frames decode**. All **47 subtitle cues** preserve the
  narration words; actual synthesized word events match the explicit 16 kHz
  guide WAV. Decoded audio peak is 0.7773, RMS −20.71 dBFS, non-silent and unclipped.
  MP4 fast-start metadata precedes media data.
- Actual browser playback advances with no media error. Byte-range serving fixes
  chapter seeking; a seek to 45.75 seconds reaches readyState 4. Exact whole-video
  bytes, bounded/suffix ranges, rejected unsatisfiable ranges, read-only requests
  and blocked traversal were checked on the six-file localhost-only player.
- Fresh extracted source-evaluation replay recomputes **22 paired tests**, checks
  **45 independent profiles / 145,041 events**, and rescores all 16 model and 16
  baseline runs without inference. The video displays this actual completed result.
- All **172 checked application, worker, source-case and UI files** remain equal
  to the preceding reviewed source release. The 211-test application/12-check
  frontend baseline was not rerun because this milestone changes media/docs only.
- The 30-file private review kit's exact members and hashes were rechecked after
  packaging. Assets, manifests, media/HTTP receipts, screenshots and authored
  source are under `artifacts/demo/20261026-review/`. It is explicitly an edited
  still-frame walkthrough with synthetic guide speech. Human listening review,
  continuous screen recording/final narration and public upload remain open.
- Zero new model calls, paid services, Docker execution or publication. No remote
  repository action was attempted. Temporary preview/player servers are stopped
  after verification; the user's port-8000 app is untouched.

## Claim audit

- **211 Python tests passed in 152.641 seconds.** Nine new trust-boundary tests
  check exact field citations, separate denominators, unresolved coverage,
  optional-reference context and rejection of rehashed fabricated conclusions,
  dropped questions/policies and changed citations. The read-only API test
  confirms no credentials, provider, worker or job, and hides all claims when
  source verification fails.
- A separate pinned fingerprint anchors the static source audit even if a local
  manifest is rehashed. This does not change the frozen study or its numerical code.
- Browser checks pass for filters (5/2/2), exact paired-record expansion, all four
  original source cards, heading focus, and direct fresh-evaluation/source-slice
  navigation. At 390×844, page width and scroll width are both 375 CSS pixels,
  including an expanded long citation. The browser error console is clean.
  Screenshots: `artifacts/ui/counterlab-claim-audit-desktop.png` and
  `artifacts/ui/counterlab-claim-audit-mobile.png`.
- All **12 frontend checks** and both interface builds pass. Full regression
  output: `artifacts/ui/claim-audit-tests.log`. The frozen kernels, planning
  protocols, model outputs and prior scores are unchanged.
- Five questions are developer-framed; statements are deterministic projections,
  not autonomous extraction or model judgments. Audit verification rederives
  statements but does not rerun every long source/oracle experiment.
- No new model credits, Docker execution, reference retrieval or publication.


## Bounded experiment workbench

- **201 Python tests passed in 97.970 seconds.** Nine new numerical/portable
  tests cover the witness, controls, small independent optimum, strict bounds,
  code/commitment mismatches, prediction isolation, full replay and rehashed
  fabricated counts. The API test verifies no provider, worker or saved job.
- **Four plan-commitment frontend tests and all eight archive-integrity tests
  passed.** A Python-generated canonical-byte/hash fixture matches JavaScript.
  Both builds pass. The runner contains only allowlisted own code and MIT license.
- Standalone execution with PYTHONPATH cleared runs a plan, verifies its complete
  result, rejects changed measurements and refuses output overwrite.
- Browser checks exercise wrong predictions and a 4-slot/96-request uniform
  trace (request seed 17, algorithm seed 5). Inverted/perfect forecasts yield
  30/30 versus 12/12 misses; offline optimum is 12. A 17-slot draft is blocked.
  Edits invalidate commitment and retain original result labels. New results
  receive focus; result downloads are bound to the selected record.
- Desktop and 390×844 checks pass: document width 375, no workbench overflow.
  Portable-plan and release handoff receipts are saved with the new archives.
  No new inference, Docker or frozen-result changes are part of this milestone.

## Evidence library and checked downloads

- **191 Python tests passed in 109.288 seconds**. The catalog matches exactly the
  eight fixed exports and distinguishes real model records from simulation.
  Opening the catalog invokes no model, credential configuration or experiment.
  An actual ZIP response's advertised checksum and size match its complete body.
- **Eight frontend integrity tests passed**: complete streaming, same-size
  tampering, truncated/oversized streams, HTML/wrong signatures, invalid/missing
  metadata, HTTP failures and cancellation before/during streaming.
- Both production builds pass. The manual-only publication workflow includes
  these unit tests, retaining its public-repository guard and permissions.
- Live browser inspection prepared a checked source-evaluation ZIP and a session
  receipt. The label explicitly distinguishes checking bytes from recomputing
  experiments. Portable delivery, altered-file behavior and mobile receipts are
  recorded with the current release after inspection.
- No frozen numerical implementation, model result or evaluation score changed.
  No new inference, Docker or reference-data request. Existing GitHub credentials
  need reauthentication (HTTP 401); no upload was retried for this milestone.

## Trace explorer and first-run usability

- **187 offline tests passed in 147.637 seconds.** Five new trace tests verify
  exact pinned event bytes, real cache membership, cumulative counts, known
  milestones, equal-outcome controls and altered-evidence rejection. The API
  test confirms read-only access with credentials, model transport and worker
  readiness blocked, and HTTP 409 when verification fails.
- Both production builds pass. The local interface opens the guided tour by
  default and retains direct links to the other views. The optional explorer
  clearly separates its constructed inputs from the source-evaluation example.
- Desktop browser inspection verified request 29's different eviction choices
  and history values. Request 30 shows 19 versus 18 misses. The all-fit control
  finishes at 4/4; the perfect-advice control changes history at request 6 but
  has no decision or cost difference. Keyboard End and case-reset behavior pass.
- At 390×844, the document is 375 pixels wide with no overflowing trace element.
  Screenshots are in `artifacts/ui/counterlab-trace-desktop.png` and
  `counterlab-trace-mobile.png`. The definitions disclosure exposes fingerprints,
  scope and a browser-generated full JSON download.
- The new `/api/trace-explorer` route is included in the portable snapshot
  allowlist. Its frontend explicitly distinguishes local recomputation from
  packaging-time verification. Release and private-upload receipts are saved
  with each new local release, separately from the source package.
- Zero new model or Docker calls; no frozen numerical implementation, model
  results or evaluation scores changed. The existing port-8000 server is kept.

## Publication-preparation update

- **181 offline tests passed in 164.991 seconds**, including ten reference and
  recursive archive checks plus a missing-reference source-view check. The
  download-attempt label was then clarified and its targeted tests rerun.
- Both normal and evidence production builds pass. New exports and source
  selection omit the full upstream numeric artifact; the site links its full
  source ZIP. The latest release's `release-summary.json` records recursive
  distribution checks; final HTTP/source/replay checks are in `verification.json`
  beside the archives after verification.
- With the optional file absent, core source inspection verifies the frozen
  local comparison and explicitly withholds the full upstream identity claim.
  An explicit helper verifies a user download; no import or startup retrieves it.
- Fresh source extraction with the full reference absent passed the core API and UI checks; the source view returned three frozen comparison rows with full-artifact identity verification false. Actual HTTP source and source-replay downloads matched their packaged ZIPs. The explicit real reference download verified 29,354 bytes against the pinned SHA-256, without an inference key or paid service.
- The manual-only Pages workflow and narration are prepared locally. Remote
  GitHub/Linux execution, actual public URL and recording/upload remain pending.
- Older archives described below predate the new reference distribution policy.
  Do not use them for publication.

## Earlier portable-release checks completed

- **170 offline tests passed in 121.099 seconds.** Eight new release boundary
  tests cover altered/missing/unexpected files, invalid paths, source allowlists,
  static subpaths, blocked mutations and unavailable evidence. Existing frozen
  algorithm, workflow, reporting and record checks remain passing.
- Normal and recorded-evidence production builds passed TypeScript and Vite.
- The release collector verified 13 fixed JSON routes and eight replay downloads
  through fresh read-only API state. Credential loading, provider transport and
  worker methods were replaced with functions that fail if called. No private
  workspace history was loaded or modified.
- An extracted judge ZIP passed its standard-library whole-site file verifier.
  Every source ZIP entry matched its separate source manifest.
- A separately extracted source ZIP served the compiled interface and favicon,
  workspace metadata, recorded demonstration, source evaluation and latest
  guarded investigation. The API rejected starting a source investigation.
  Imports came from the extracted source root; the existing pinned Python
  dependency environment was reused. A new dependency installation was not tested.
- Browser inspection passed under `/counterlab/`, exercising the relative asset,
  JSON and download paths needed by a project static host. All main views, both
  evaluations, all three research views and demonstration download links loaded.
  Phone inspection at 390 × 844 had no document horizontal overflow.
- Actual HTTP evaluation download matched the packaged ZIP byte for byte. A fresh
  extracted replay passed **22 paired tests, 45 independent profiles and 145,041
  post-warmup events**, rescoring 16 baseline and 16 model runs with no inference.
- In a disposable served copy, adding one whitespace byte to a snapshot while
  retaining the manifest made the browser reject the record with an integrity
  error. The release archive was not altered. This checks consistency relative
  to the manifest; an attacker replacing both files is outside that guarantee.

## Practical limits

This is local verification, not a public hosting or Linux/CI availability test.
The snapshot collector runs each API's existing checks; the long source-regime
view verifies its frozen record and aggregates rather than reexecuting all long
traces at packaging. Its portable download contains that full replay.

The evidence build itself performs no fresh inference or numerical execution.
The latest guarded example retains its simulated-planning label. No model quality
improvement, general ranking, theorem or full research reproduction is claimed.

No new model requests, cash charges, external uploads or submission occurred.
The user's separate app server was left running. Public source/build/video links
and the upstream numeric artifact's redistribution review remain pending.

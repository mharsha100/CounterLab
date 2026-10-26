# Local release validation — October 26, 2026

## Clean installation and project freeze

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

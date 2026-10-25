# Second Look — delivery and evaluation plan

> October 16 update: this remains the plan for the Second Look alternative. The current ambitious direction has a separate [CounterLab delivery plan](COUNTERLAB_DELIVERY_PLAN.md).

**Prepared October 15, 2026. Planning only; no setup, development, or evaluation has run.**

This plan implements [the PRD](PROJECT_PRD.md). Research and prior-art conclusions are in [the decision memo](RESEARCH_AND_DECISION.md). Assume approximately three focused human hours per day from October 16–29: **42 hours**, with October 30 reserved for emergencies. This is a planning estimate, not a commitment that every task will fit.

## 1. Build sequence and decision gates

| Date | Hours | Deliverable | Exit condition |
| --- | ---: | --- | --- |
| Oct 16 | 3 | Account/model access and first narrow feasibility run | Actual Nemotron function call through Nebius; one development-only availability probe and validated proposal |
| Oct 17 | 3 | Contract schema and fixed experiment runner | One supported experiment can execute with pinned rows/seed; approval binds a proposed change; decide Gate A |
| Oct 18 | 3 | Evidence tools | Availability, bounded target-relation, and temporal split checks have known positive/negative examples |
| Oct 19 | 3 | Agent loop and uncertainty handling | Model selects tools, reacts to outputs, and abstains on missing timing; invalid actions rejected |
| Oct 20 | 3 | Second public dataset, generic-input smoke test, and clean cases | Same engine handles Bike, Bank and an unfamiliar synthetic CSV/manifest; no dataset-specific diagnosis branches; decide Gate B |
| Oct 21 | 3 | Main React journey | Choose case → confirm task → inspect evidence → approve revision → view result |
| Oct 22 | 3 | Freeze/export/reproduction | Final evaluator isolated from agent tools; package reproduces the pinned run |
| Oct 23 | 3 | Local adapter packaging and hosted version | Earlier generic-input path has documentation/export; public endpoint exists; verify hosting/cost/uptime path |
| Oct 24 | 3 | Evaluation suite and recovery paths | Frozen case definitions, scoring rules, baseline harness, API/worker errors covered |
| Oct 25 | 3 | Development ablation and model selection | Select prompt/model using development cases only; publish design choices; freeze candidate |
| Oct 26 | 3 | First withheld-case evaluation | Record all outcomes, failures, latency, and cost; decide Gate C; feature freeze |
| Oct 27 | 3 | Reliability and judge walkthrough | Ten end-to-end runs, fresh-browser access, local reproduction, screenshots; resolve only concrete defects |
| Oct 28 | 3 | Video, description, README, feedback | Complete 2:45–2:55 video draft; every claim linked to evidence |
| Oct 29 | 3 | Final compliance review and submission | Public repository/demo/video checked; submit and preserve confirmation/version |
| Oct 30 | Buffer | Only critical submission fixes | Hard deadline: **1:00 p.m. EDT**; avoid relying on this buffer |

### Gate A — by the end of the first two sessions

Require a real model/tool/runner round trip, one supported correction, and one unresolved case. The model must do more than rewrite a static warning. Test semantic task interpretation on development prompts with different timing assumptions.

If Lightning is inadequate, test one other available Nemotron model on the same development tasks. If the bounded loop still fails, revise the scope and recommendation before building a full interface. Do not spend a week polishing an unproven core.

### Gate B — by October 20

The second dataset and one unfamiliar synthetic CSV/manifest must work without per-dataset diagnosis code. A clean example remains unchanged; an unknown timing field remains unresolved. A feature-only rerun must preserve all other evaluation settings. Profile the classification case and a high-cardinality input against the intended host's resource limits before adding UI polish. If a temporal repair is not reliable, cut it to **detection and explanation only**, then update the PRD and submission claims. Feature-availability repair remains essential.

### Gate C — October 26

Assess the frozen suite and deployment path. Keep the core approval, provenance, reproduction, and live sponsor integration. Cut browser upload, notebook import, group splitting, additional models, visual embellishments, and extra integrations before cutting those essentials.

If a required feature is cut, publish the narrower supported scope. If no reliable live agent workflow exists, the original quality bar has not been met; do not represent a saved walkthrough as the complete product.

### Work split

The human entrant owns account/payment decisions, task assumptions, review of outputs, final narration, and submission. AI assistance supports implementation, research, tests, review, and documentation. The entrant should be able to explain the data flow, why the evidence supports each finding, and the limits of the evaluation.

## 2. Evaluation protocol

### A. Freeze the task definition first

Create a versioned **Second Look challenge suite v1** with 24 cases: eight development cases and sixteen withheld challenge cases. These are our controlled scenarios over public datasets and synthetic fixtures, **not an established independent public benchmark**. Preserve the generator/specification, random seeds, data provenance, and labels.

Withheld suite composition:

| Case group | Cases | Expected behavior |
| --- | ---: | --- |
| Feature availability violations | 6 | Identify specified unavailable features, cite the confirmed timing/evidence, propose only allowed exclusions |
| Temporal evaluation mismatch | 4 | Identify mismatch only when the task requires future prediction and time metadata is sufficient |
| Clean controls | 4 | Avoid a false confirmed finding and avoid unnecessary changes, including for legitimate strong predictors |
| Ambiguous timing | 2 | Ask for missing information or mark unresolved; do not invent availability or apply a repair |

Include name changes with equivalent dictionaries, task-wording changes, a negative high-correlation control, and metadata containing irrelevant instruction-like text. Within the counts above, include a **same-schema contract pair**: a synthetic field becomes available after stage one, while the outcome occurs at stage two. Change only whether the prediction occurs before or after stage one; the feature-availability conclusion must change accordingly. This tests reasoning about the contract rather than recognition of a familiar column name.

Use at least two public schemas plus synthetic data. Cases sharing a base dataset are correlated: report results by dataset and failure family, not as sixteen independent real-world deployments. Renaming a familiar public dataset does not prove the model has never encountered its content.

For every case, author the expected contract fields, required and forbidden findings, acceptable revision or abstention, and required run outcome before evaluation. Keep these expected labels and grader logic outside the agent's inputs and accessible tools. Score the model's contract draft **before** user/harness confirmation, so correcting its interpretation does not conceal a mistake. Freeze prompt, model, limits, estimator, splits, and metrics before running the withheld suite. In a solo project this is a procedural separation, not an independent third-party blind study. Record whether any case was inspected during development.

### B. Three comparisons

1. **Rules only:** execute the supported deterministic checks with a confirmed structured contract. This is a strong baseline for detection; it may match or exceed the agent. Do not deliberately weaken it.
2. **Model without tools:** same Nemotron version, task, dictionary, and permitted metadata; model proposes a finding/change without executing probes. Grade grounding and permitted-action correctness, not fluent explanations.
3. **Full workflow:** semantic contract assistance, evidence selection, tools, bounded revision, and verified execution.

Report information access explicitly. A rules engine supplied with a perfect structured contract is an oracle for contract interpretation, not a fair measure of natural-language usability. Separately score the model's contract mapping against expected fields. Do not claim “better detection than rules” if the actual contribution is helping specify and execute the review.

Run each configuration three times per withheld case where meaningful. There are 48 full-agent trials and 48 model-only trials; deterministic rules need one run per case plus reproducibility checks. Use the same supported inputs and case definitions. Report successful trials per case, not just the best of three.

This approach is informed by [Anthropic's agent-evaluation guidance](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents): evaluate outcomes and execution records, combine appropriate graders, and account for stochastic runs. Our small suite supports a scoped engineering claim, not a broad capability ranking.

### C. Metrics and provisional release thresholds

| Metric | Definition | Target before strong claims |
| --- | --- | --- |
| Complete-case success | Correct contract handling, required findings, no forbidden action, correct revision/abstention, successful required run and usable report | At least 39 of 48 full-agent trials; report case-level outcomes as well |
| Contract draft correctness | Required fields correctly mapped or appropriately left unknown before confirmation | Report exact field/case counts separately from the corrected contract; no masking through user edits |
| Finding precision | Correct confirmed findings / all confirmed findings | At least 90%; always show counts |
| Positive-case recall | Positive cases with the required supported finding / all supported positive cases | At least 80%; show each family separately |
| Clean-case false positives | Clean cases receiving a false confirmed finding | 0 of 12 trials across four cases; small sample caveat |
| Ambiguity handling | Ambiguous cases left unresolved without an executed repair | 6 of 6 trials across two cases |
| Grounding | Confirmed findings with valid evidence and contract references | 100%; valid reference alone is insufficient if inference contradicts evidence |
| Revision correctness | Proposed revisions that satisfy the expected invariant and run successfully | At least 90% on supported repair cases |
| Unauthorized execution | Unapproved or non-allowlisted changes executed | Zero |
| Reproduction | Exported runs reproducing deterministic metrics within 1e-6 | All sampled frozen outputs |
| Cost and latency | Median, range, and p95 of measured complete runs | Typical ≤90 sec; average inference ≤$0.10; report sample size |

Deduplicate repeated descriptions of the same finding. Report abstentions, malformed outputs, timeouts, and infrastructure errors separately; include failures in end-to-end success denominators. Do not count a failed run as a clean pass. Automated evaluation simulates the approval event for eligible proposed diffs inside the test harness; separately test that a missing or mismatched approval cannot execute a revision in the application.

After looking at withheld outcomes, fixes make that suite a regression suite. Label subsequent results accordingly. Use newly frozen additional cases if claiming a new withheld evaluation, and report both original and revised results. No repeated tuning against a test set while continuing to call it untouched.

### D. Experiment-level final data

Use the PRD's separate training/development/final protocol. The agent never sees final labels or score during investigation. The evaluator scores only after user approval and protocol freeze. If historical test reuse cannot be ruled out, mark independence unverified. Track exposure across sessions and revisions by dataset snapshot, target and final row IDs; a different feature/model configuration does not reset it. Hosted example results become illustrative/reused after first exposure. A cached or repeated result is explicitly a reproduction, not new independent evidence.

For Bike, compare removal of target-derived features on the **same development row allocation**. Show any random-to-chronological validation change as a separate policy comparison. For Bank, the pre-call duration check does not require inventing a full timestamp from month/day fields. Do not claim that its IID-style demonstration establishes future-campaign performance or rules out repeated-customer dependence.

### E. Verification beyond model correctness

- Fresh-browser start-to-export walkthrough with no personal key or paid login.
- Modified prediction contract changes real tool decisions and results where applicable.
- Clean case, ambiguous case, and unsupported input all have useful UI outcomes.
- Secret scan of repository, exported reports, screenshots, and client requests.
- API rate limit/timeout and invalid JSON handled without fabricated results.
- Reproduction from a clean environment using the documented input format.
- Check key tables and controls with keyboard navigation and a small browser viewport.

These are necessary release checks. Self-performed walkthroughs do not count as independent usability testing or customer validation.

## 3. Budget and ongoing availability

### Inference estimate

The [Nebius catalog](https://nebius.com/services/token-factory/models/nvidia-nemotron-models-inference) listed Lightning at **$0.06 per million input tokens and $0.24 per million output tokens**, and Super at $0.30/$0.90, when researched. Recheck before use.

Illustrative aggregate usage per audit: 40,000 input tokens and 8,000 output tokens across all requests.

| Model rate | Arithmetic | Estimated inference per audit | 1,000 audits |
| --- | --- | ---: | ---: |
| Lightning | 0.04 × $0.06 + 0.008 × $0.24 | $0.00432 | $4.32 |
| Super | 0.04 × $0.30 + 0.008 × $0.90 | $0.01920 | $19.20 |

These are arithmetic scenarios, not observed usage or an invoice forecast. Retries, reasoning tokens as billed, longer histories, model changes, and traffic can change the total. Count provider-reported usage; configure output/request limits and a service-side spending ceiling.

Plan against **only $25 of Token Factory credit after it is actually granted**, with a proposed $10 development/evaluation allocation and $15 retained for judging. The additional advertised Builders Program credit is contingency until confirmed. Actual credit expiry must cover the judging window. CPU hosting, storage, and any bank-card charges are separate; no purchase has been made or authorized.

The host must support a working public demo through **December 15**, not only the submission day. Prefer one small CPU service; decide the provider after checking sleep/uptime, memory, storage, and price. A saved example improves resilience but does not replace the working application. Choose a sustainable hosting plan before October 23; record the ongoing cost and required user decision during setup.

The [current billing documentation](https://docs.tokenfactory.nebius.com/other-capabilities/billing-new) should be checked in the actual account before activation. A promotional balance is not proof that overage charging is disabled.

## 4. Three-minute demonstration storyboard

**Target duration: 2:50.** All numbers must come from a real recorded run. Any skipped waiting time is disclosed by the edit; no reenacted result is presented as live output.

| Time | Visual/action | Narration purpose |
| --- | --- | --- |
| 0:00–0:18 | Prediction question and actual original development score, labeled as our deliberately flawed example | Explain the AI builder's problem: a score can look persuasive while answering the wrong question |
| 0:18–0:38 | Confirm before-the-hour contract and feature timing | Establish precisely what the model is meant to know |
| 0:38–1:05 | Live investigation, selected tool, numerical evidence | Say aloud that NVIDIA Nemotron on Nebius Token Factory chooses and interprets the evidence tools |
| 1:05–1:30 | Finding with source/contract evidence and exact diff | Explain the unavailable features; the numerical identity supports the finding |
| 1:30–1:55 | Approve and rerun under fixed development settings | Show a real action and measured result; explain that a score decline is not itself proof |
| 1:55–2:20 | Freeze/final result and export | Show the reproducible record and what the assessment does and does not establish |
| 2:20–2:40 | Second case, clean control, or unknown-timing case | Demonstrate reuse and restraint; avoid a long second tutorial |
| 2:40–2:50 | Evaluation summary with actual denominators | State tested scope, strongest measured result, and user outcome |

If both split and feature problems make the video confusing, use feature availability as the main story and leave split-policy evidence in the app/writeup. Good explanation is more valuable than cramming every feature into the video.

The [organizer asks](https://nebiusglobalaihackathon.devpost.com/updates/46205-how-to-build-a-winning-project) for a pitch-like demonstration, explicit audible sponsor/model use, and specific feedback. Record readable screen text, clean audio, and captions. Use the exact model actually serving the application in the final narration and Built With section.

## 5. Submission package

Create during implementation:

- Public repository with LICENSE, complete source, dependency locks, environment template, README, examples, attribution, and clear reproduction instructions.
- Public app URL and a judge guide with the shortest complete path.
- Public YouTube demo under three minutes.
- Devpost description: user/problem → working workflow → architecture and sponsor role → measured evidence → prior art/difference → limitations → next steps.
- Evaluation report with version, exact cases, baselines, repeated trials, denominators, failures, cost, and latency.
- Tool feedback based on actual observations: onboarding steps/time, exact endpoint/model, schema/tool-call behavior, error handling, quality/latency/cost tradeoffs, and actionable improvements. Mark unused services as not used.

No fabricated user quotes, time savings, adoption, benchmark wins, or “world-first” claims. Describe simulated bugs and controlled scenarios as such. Cite the source data separately from our new experiment recipes.

### Final compliance check

Confirm eligibility, join status, correct track, live required technology, working free judge access, repository visibility/license, data permissions, video visibility/duration, English materials, feedback fields, and successful submission confirmation. Recheck the [rules](https://nebiusglobalaihackathon.devpost.com/rules) and [FAQ](https://nebiusglobalaihackathon.devpost.com/details/faqs) before submission. Keep the submitted version identifiable and the demo accessible during judging.

## 6. Preparation for the entrant

Learn only what supports the next milestone. Before building each part, be able to explain:

1. **Prediction-time availability:** why a field can be useful in an offline table yet unavailable when an actual prediction is needed.
2. **Validation design:** what random and chronological splits estimate, and why a final test cannot guide repair selection.
3. **The agent boundary:** what Nemotron decides, what Python proves, and what still requires the user's knowledge.
4. **Reproduction:** why data/version/row allocation/seed/metric must travel with a result.
5. **Product communication:** explain one finding in 30 seconds without relying on jargon.

Practice answering: “Why not just use a static checker?”, “How do we know the model did useful work?”, “What if the metadata is wrong?”, “Why did the score get worse?”, and “What have you actually measured?” The documents provide the basis; the final answers must reflect the implemented product and actual results.

## 7. Principal risks and responses

| Risk | Early signal | Response |
| --- | --- | --- |
| Model is decorative | Same canned tool sequence and generic prose on every case | Test semantic contract tasks and evidence-dependent choices; revise before UI polish |
| Familiar examples look scripted | Only known Bike feature names work | Generic manifest adapter, second schema, renamed columns, clean/unknown cases |
| Scientific overclaim | Claiming the score drop proves leakage or split change improves the model | Require contract evidence and separated comparisons |
| Scope exceeds time | Notebook parsing, many estimators, or multiple services appear | Keep fixed templates and two issue families; follow cut order |
| Final test becomes a tuning set | Repeated revisions after viewing final results | Permanently label revealed tests; use new data for new independent claims |
| Hosting/credit failure | Sleep, memory pressure, expired credits, quota errors | Profile early, verify plan/expiry, preserve labeled example and runbook |
| Impact evidence is weak | Claims of users/time saved without observations | State problem evidence and measured capability; acknowledge demand remains untested |

**The immediate next phase is setup and Gate A. This document does not start that work.**

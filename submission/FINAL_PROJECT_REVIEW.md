# Final project quality review — October 26, 2026

The entrant requested one final project-wide improvement and acceptance pass
before submission work. This completed the reopened countdown step 3. It does not
change the research question, frozen model scores or private-publication policy.

## Research applied

This is a targeted review of authoritative guidance and relevant repositories,
not a claim to have examined every repository or to have proved an optimal design.

| Guidance | Application to CounterLab |
| --- | --- |
| [W3C text contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) and [non-text contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html) | Darken small safety disclosures, errors, consent text and keyboard focus indicators while retaining the existing visual design. |
| [W3C skip links](https://www.w3.org/WAI/WCAG22/Techniques/general/G1) and [status messages](https://w3c.github.io/wcag/understanding/status-messages) | Add skip-to-main access, intentional route focus and an announced checked-download result with a stable button. |
| [React error boundaries](https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary) | Catch rendering failures and show a safe reload action, including unsaved-edit and running-job implications. No raw response details are exposed. |
| [MDN abort timeouts](https://developer.mozilla.org/en-US/docs/Web/API/AbortSignal/timeout_static) | Bound the portable manifest read and allow a later explicit read after a transient failure, without silently retrying paid work. |
| [OWASP ASVS repository](https://github.com/OWASP/ASVS) | Use input validation and boundary review as prompts for targeted tests; no claim of ASVS certification or comprehensive security audit. |
| [Python Windows locks](https://docs.python.org/3.13/library/msvcrt.html#msvcrt.locking), [Unix locks](https://docs.python.org/3.13/library/fcntl.html#fcntl.flock) and [Pydantic validators](https://docs.pydantic.dev/latest/concepts/validators/#field-validators) | Hold a single-writer workspace lease through job shutdown and require an actual JSON boolean for spending consent. |
| [NVIDIA NeMo Guardrails](https://github.com/NVIDIA-NeMo/Guardrails) and [execution rails](https://docs.nvidia.com/nemo/guardrails/latest/about-nemo-guardrails-library/rail-types) | Validate worker results before they enter evidence or planner feedback. Reuse the existing small deterministic harness; no extra framework dependency is needed. |
| [Agent evaluation guidance](https://www.anthropic.com/research/demystifying-evals-for-ai-agents) and [Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai) | Retain deterministic grading, complete trajectories, failed attempts and non-AI baselines. Preserve the limitations of the eight-task development evaluation. |

## Implemented improvements

- Nested view URLs, refresh and Back/Forward work together; view titles and
  keyboard focus follow navigation.
- Source-record read failures offer an explicit refresh of the same saved run.
  Download completion is announced without replacing the focused check button.
- A rejected manifest request no longer poisons all later reads until reload.
  A rendering error now has an understandable recovery screen.
- A second writable app cannot recover another process's running jobs. Read-only
  inspection can coexist. A crashed owner releases its OS lock automatically.
- Numeric `1`/`1.0` cannot substitute for explicit credit consent. Output-token
  limits require actual integers.
- Worker measurements are compared with independent host replay using canonical
  JSON hashes, so `false` or `0.0` cannot silently substitute for integer `0`.
  Invalid results are rejected before evidence receipts or planner feedback.
- Two source-workflow diagnostics reached the original 15-second worker deadline
  before producing results. A separately versioned execution profile allows 60
  seconds for each new guarded source replay, with two replays per admitted test.
  Probes and legacy short experiments keep 15 seconds. Memory, CPU, network,
  filesystem and process restrictions remain fixed; no retry was introduced.
  A separate verifier records the new limits while preserving historical v2 code
  and receipts. The failed diagnostics remain available locally.

Pinned algorithms, original model responses, numerical observations and frozen
scores are unchanged. The guard's live model quality remains unmeasured. Software
hardening does not establish stronger reasoning, scientific validity or a win.

## Verification

Final local acceptance passed on October 26:

- **241 Python tests passed in 200.722 seconds**, plus **18 frontend tests** and
  both production builds. The Windows crash test now exits the actual owner
  process abruptly, avoiding the virtual-environment launcher; its five ownership
  checks also passed three consecutive runs. Production locking was unchanged by
  that test repair.
- Real browser checks covered nested navigation, refresh, Back/Forward, titles,
  keyboard focus, the skip link, checked downloads, a failed saved-record read
  and rendering-error recovery. Failure recovery issued no run-start requests.
  At 390-pixel phone width the source view had no horizontal document overflow.
- Restricted Docker checks passed. The new source integration rejected one
  synthetic prediction, measured one experiment twice (**30.187 / 28.884 seconds**),
  then passed standalone portable replay. It used simulated planning and **zero
  model requests**; this is execution evidence, not a model-performance result.
- The extracted source passed in the previously fresh locked Python environment.
  The included interface, new execution contract, old record/export and missing
  optional-reference state were checked. All three run-start routes rejected
  writes in read-only mode; credential and provider access were blocked.
- Release collection verified **17 snapshot routes and eight replay packages**.
  All 100 historical case files and the eight replay packages' member contents
  match the earlier accepted release. Their earlier complete numerical replays
  still apply; no frozen evidence was regenerated or replaced.
- npm reported zero known advisory matches; OSV returned no matches for the 17
  locked Python packages. No dependency upgrades were needed.

Detailed logs and browser-review fixtures are local under
`artifacts/freeze/20261026-final-review/`. The new release is
`artifacts/releases/counterlab-final-review-20261026/`; its acceptance receipt and
release summary bind the checks to the archive hashes. Earlier failed diagnostics
and the initial process-targeting test failure remain in the local review logs.

The dependency checks query public npm/OSV advisory data for pinned versions.
An empty advisory result means no reported match at check time, not proof of
absence of vulnerabilities. No dependencies were upgraded speculatively.

## Adoption

The reviewed source is frozen locally. The existing private GitHub commit remains
the prior release; updating it is part of the next submission step. No upload or
public deployment occurred in this review. Existing frozen ZIPs were not overwritten.

Restart the old local app when adopting the reviewed release. An already-running
old process cannot enforce the new workspace lock. Windows behavior is exercised
locally; Unix locking and hosted deployment still need their own environment
validation. No model credits are used in this review.

**Countdown: 5 remaining — 0 project steps, 5 submission steps.**

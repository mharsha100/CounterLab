# Second Look — research and project decision

> October 16 update: this records the earlier decision. The new [ambitious comparison](AMBITIOUS_IDEA_COMPARISON.md) recommends CounterLab subject to explicit experimental gates, and preserves Second Look as the narrower alternative.

**Research date: October 15, 2026. Decision: recommend Second Look for Best Apps and Agents.**

This is a researched product recommendation, not a claim that the idea is globally unique or guaranteed to win. No accounts, application, experiments, or benchmark results were created during this research. The next phase is setup and a short feasibility test, followed by implementation.

## 1. The recommendation

**Second Look helps an AI builder investigate whether a score from a supported tabular experiment supports the prediction they actually intend to make.** The builder states when the prediction happens and what information exists then. NVIDIA Nemotron, served through Nebius Token Factory, chooses evidence-gathering tools, proposes a bounded correction to the experiment, and explains the result. Deterministic Python verifies findings and reruns a fixed experiment. The user receives the changed specification, measured results, limitations, and a reproduction package. P0 supports its documented model recipes; it does not reproduce arbitrary existing notebooks or models.

Positioning: **Before you trust the score, test the experiment.**

The intended first user is an AI learner or solo builder preparing a tabular ML result for a portfolio, internal review, or prototype handoff. This matches the entrant's Python, data, and React/TypeScript strengths. We have no access to recruited users, so the initial case for usefulness rests on published problem evidence and reproducible demonstrations; product demand remains unvalidated.

The proposed product experience is an experiment-specific claim-review workflow: prediction contract → targeted investigation → evidence → approved revision → controlled rerun → reproducible record. Both its leakage checks and the general investigate/repair/verify pattern have prior art, including the winner examples below. The project must earn differentiation through the connection between prediction timing, evaluation policy, and an honestly interpreted revised score.

## 2. What the actual competition tells us

The live event showed **23,493 registrations** when checked. The gallery was unpublished. Registrations, overlapping skill tags, and people marked solo cannot establish how many eligible projects will be submitted, their quality, or our winning odds. There are no winners from this still-open edition to study. We therefore examined comparable, completed events. [Event overview](https://nebiusglobalaihackathon.devpost.com/), [gallery](https://nebiusglobalaihackathon.devpost.com/project-gallery).

The official judging framework has four equal criteria: implementation, design, impact, and idea quality. The organizer emphasizes complete autonomous workflows, meaningful sponsor integration, and a concise demonstration. A technically elaborate project with an unclear job or unreliable demo can lose substantial ground. [Judging explanation](https://nebiusglobalaihackathon.devpost.com/updates/46204-here-s-how-judging-works).

### Comparable winners: verified awards, bounded conclusions

| Project | Verified result | Publicly described work | Lesson for our entry |
| --- | --- | --- | --- |
| MediSimplifier | Nebius Serverless AI Builders Challenge, first | Discharge-document simplification; training, evaluation, public code | Connect an understandable problem to measured outcomes |
| Evaluation dashboard, Andrei Goldenberg | Same event, second | Compares quality, latency, and deployment/inference cost | Make technical tradeoffs visible |
| Balagan | Same event, third | Multi-agent fault injection, recovery experiments, measured cost | Evidence and a visible failure/recovery sequence are persuasive |
| Route Optimization Agent | NVIDIA NeMo Agent Toolkit hackathon, first | Language constraints become optimized routes, simulation, and robot behavior | Show an end-to-end action with central sponsor technology |
| OpenCodeReview | Same NVIDIA event, second | Configurable code/security review with orchestration and memory | Developer workflows can be competitive when coherent |
| EcoLafaek | AWS AI Agent Global Hackathon, first | Waste reports, image interpretation, agent analysis, maps | A concrete audience makes impact easier to understand |
| AegisAgent | Same AWS event, second | Insurance evidence and policy analysis produce a cited decision packet | Evidence-backed output can be the product |
| Project Blackbox | DataHub agent hackathon, grand prize; solo entrant | Investigate a data incident, verify cause, repair, test, record | Solo scope can succeed; make correctness inspectable |
| Launch Control | GitLab hackathon, Easiest to Use | Release assessment, dashboard, remediation issues | Usability and an actionable next step matter |

Award sources: [Nebius announcement](https://nebius.com/blog/posts/serverless-ai-builders-challenge-winners), [NVIDIA announcement](https://developer.nvidia.com/blog/hackathon-winners-bring-agentic-ai-to-life-with-the-nvidia-nemo-agent-toolkit/), [AWS announcement](https://aws-agent-hackathon.devpost.com/updates/38140-congratulations-to-the-winners-of-the-aws-ai-agent-global-hackathon), [DataHub announcement](https://datahub.com/blog/meet-the-winners-of-build-with-datahub-the-agent-hackathon/), [GitLab announcement](https://gitlab.devpost.com/updates/41783-meet-the-winners).

Submission evidence: [EcoLafaek](https://devpost.com/software/ecolafaek), [AegisAgent](https://devpost.com/software/aegisagent-an-insurance-claim-app-fully-developed-by-kiro), [Project Blackbox](https://devpost.com/software/project-blackbox), [Launch Control](https://devpost.com/software/launch-control-bgp8az). These pages include demos or links and implementation claims. This research inspected published descriptions; it did not independently reproduce their metrics or verify every demo interaction.

**Inference:** A specific job, an observable action, understandable evidence, and polished delivery recur in this selected sample. These are useful design choices, not a statistical account of why projects won. Organizer writeups and successful entries have selection and promotional bias. We lack score sheets and a comparable sample of unsuccessful entries.

We should also avoid copying winner scale. MediSimplifier extended earlier work and reported spending beyond our initial credit allowance. Balagan is especially relevant prior winning work against choosing a generic agent-chaos project. [Nebius winner details](https://nebius.com/blog/posts/serverless-ai-builders-challenge-winners).

## 3. Research that changes the product design

| Source and evidence level | Relevant finding | Decision it informs | Limit |
| --- | --- | --- | --- |
| Kapoor & Narayanan, *Patterns*, 2023; peer-reviewed | Their synthesis found leakage affecting 294 papers across 17 fields | Treat evaluation validity as a real, documented problem | This is a lower bound assembled from prior reviews, not the percentage of all ML projects with leakage |
| REFORMS, *Science Advances*, 2024; consensus reporting guidance | Requires clarity about study goals, data, evaluation, feature legitimacy, and reproducibility | Capture the intended prediction and retain a reproducible record | A checklist does not automatically establish that an experiment is valid |
| Yang et al., ASE 2022; peer-reviewed | Static analysis detects several leakage patterns in notebooks; study analyzed over 100,000 notebooks | Existing deterministic analysis is a serious baseline | Static detection covers particular patterns and cannot infer every deployment assumption |
| LeakageDetector 2.0, 2025; tool paper/preprint | Notebook extension combines leakage detection, quick fixes, and LLM-assisted correction | A generic AI leakage fixer is insufficient differentiation | Its preliminary evaluation is not evidence that all fixes are correct |
| *The Silent Failures in Agentic Data Science*, October 2026; fresh preprint | Studies methodological errors across 220 tasks and a controlled suite | Evaluate correctness of the procedure separately from predictive score | Uses an LLM judge, limited human calibration, and a defined taxonomy; do not treat as settled prevalence evidence |
| scikit-learn documentation; primary implementation guidance | Prediction-time availability and separation of fitting from test data are essential | Use train-only preprocessing and an explicit prediction contract | Pipeline alone does not solve feature timing or inappropriate splits |

Primary reading links:

1. [Leakage and the reproducibility crisis in machine-learning-based science](https://pmc.ncbi.nlm.nih.gov/articles/PMC10499856/), [published DOI](https://doi.org/10.1016/j.patter.2023.100804). The journal's 294-paper count is used here; an earlier preprint had a different count.
2. [REFORMS published record](https://pubmed.ncbi.nlm.nih.gov/38691601/), [accessible author manuscript and checklist](https://arxiv.org/html/2308.07832).
3. [Data Leakage in Notebooks: Static Detection and Better Processes](https://www.cs.cmu.edu/~ckaestne/pdf/ase22.pdf), [author implementation](https://github.com/malusamayo/leakage-analysis).
4. [LeakageDetector 2.0 full text](https://arxiv.org/html/2509.15971v1).
5. [The Silent Failures in Agentic Data Science](https://arxiv.org/html/2610.14115v1). Its linked project-resources page did not load during the final check; importing its suite is not an MVP dependency.
6. [scikit-learn common pitfalls](https://scikit-learn.org/stable/common_pitfalls.html).

### Implications we must preserve

- A large score, correlation, or score decline does not prove leakage. A confirmed finding requires a violated assumption with supporting evidence.
- Whether a feature is legitimate depends on the task and prediction moment. Missing availability metadata should produce a question or an unresolved finding.
- A time column does not automatically require chronological evaluation. The intended generalization determines the split.
- Repair selection must not consume final test results. The final test is revealed after the protocol is frozen; later reruns are reproductions of a revealed test, not fresh independent validation.
- The tool can establish specific invariants under declared assumptions. It cannot certify all scientific validity or future deployment performance.

## 4. Prior art and the honest differentiation

| Existing work | What already exists | What Second Look must demonstrate |
| --- | --- | --- |
| [tsauditor](https://github.com/imann128/tsauditor) | Target equivalence, combinations reconstructing targets, declared availability, remediation and reports | Experiment-level contract, bounded revision, controlled execution, and a trace connecting the claim to its evidence |
| [LeakageDetector 2.0](https://arxiv.org/abs/2509.15971) | Notebook analysis and manual/LLM fixes | A guided claim-review product with a measured rerun; broader notebook support is not our claim |
| [Deepchecks train/test validation](https://docs.deepchecks.com/stable/api/generated/deepchecks.tabular.suites.train_test_validation.html) | Established leakage, overlap, and distribution checks | Context-dependent tool selection and an understandable decision with reproducible artifacts |
| [walkforward-audit](https://github.com/mospira/walkforward-audit) | Instructions for temporal experiment review, timing, and comparisons | A functioning constrained workflow with executable checks and a usable interface |

This is a competitive area. No evidence establishes that the combined workflow is globally unique. The proposed advantage is a focused user experience and rigorously demonstrated execution. Nemotron must do consequential work: interpret an incomplete task description, choose relevant probes, react to results, propose an allowed change, and identify uncertainty. If deterministic rules produce an equally useful outcome on our actual tasks, we must improve or narrow that role before making an agentic-value claim.

The familiar Bike Sharing identity is **not a discovery or new detector**. It is an illustrative case. A second dataset, renamed schemas, clean controls, ambiguous cases, and a documented local input format are required to show a reusable engine.

## 5. Alternatives considered

These assessments are planning judgments about an unbuilt product, not estimated judge scores. All four official criteria have equal weight; feasibility is an additional delivery gate.

| Direction | Implementation opportunity | Design opportunity | Impact evidence | Idea/competition concern | Solo delivery assessment |
| --- | --- | --- | --- | --- | --- |
| **Second Look** | Evidence tools, meaningful agent decisions, reproducible CPU runs | One clear claim-review journey | Strong published methodological problem; demand untested | Strong prior art; workflow must earn distinction | **Best fit** for existing skills and public-data testing |
| Accessible user-journey repair | Browser checks, source patch, rerun | Very visible before/after | Strong accessibility need | Commercial and research repair systems already exist | Browser/repo sandbox and credible test coverage increase scope |
| Generic agent rehearsal/chaos | Fault injection and replay | Clear failure/recovery demonstration | Agent reliability is relevant | Direct products and prior Nebius winner overlap | Feasible narrow slice; weak differentiation |
| Municipal commitment tracker | Source ingestion and evidence reconciliation | Strong citizen-facing story | Plausible need; no domain/user access | Must go beyond existing meeting summaries | Source parsing and validation risk within two weeks |
| README setup repair | Environment diagnosis and verified patch | Understandable developer job | Plausible workflow | Executable-doc tools and coding agents overlap | Arbitrary repository execution and hosting cost add risk |

Supporting comparisons: [SWEeper-Bench](https://arxiv.org/html/2610.14096v1), [its official runner](https://github.com/zlab-princeton/sweeper-bench), [Playwright accessibility testing limits](https://playwright.dev/docs/accessibility-testing), [Deque tools](https://www.deque.com/axe/devtools/extension/), [verified accessibility repair preprint](https://arxiv.org/abs/2608.24913), [Agent Etna](https://www.agentetna.com/), [Chaosync](https://www.chaosync.com/), [Prophecy Gov](https://www.prophecygov.com/), [NYC legislative records](https://legistar.council.nyc.gov/), [Runme](https://docs.runme.dev/getting-started/cli/).

Second Look wins this decision because we can demonstrate the complete useful action with modest CPU requirements, use primary public data, and evaluate known failure cases without recruiting users. It is not selected because ML tools automatically win hackathons or because a novel name removes prior art.

## 6. Data and platform evidence

### Public demonstration data

- [UCI Bike Sharing](https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset): `casual` and `registered` are components of total `cnt`. Under a before-the-hour demand-prediction contract, those same-hour totals are unavailable. The published data dictionary supports the semantics; our intentionally flawed experiment is a new demonstration, not an accusation against the dataset authors.
- [UCI Bank Marketing](https://archive.ics.uci.edu/dataset/222/bank+marketing): `duration` records the contact's duration. Under a before-call contract it is unavailable. The application demonstrates experiment review, not customer targeting or financial advice.
- Both UCI pages specify CC BY 4.0. Preserve attribution and record any preprocessing. Dataset licenses remain separate from the application's open-source license.

### Required technology

Nebius documents [function calling](https://docs.tokenfactory.nebius.com/ai-models-inference/function-calling) and an [inference quickstart](https://docs.tokenfactory.nebius.com/quickstart). Its [Nemotron catalog](https://nebius.com/services/token-factory/models/nvidia-nemotron-models-inference) lists public NVIDIA endpoints. This supports a practical architecture without training or self-hosting a large model. Account access, schema behavior, latency, and credits remain untested.

### Research limitations

This was a targeted primary-source review across event rules, comparable winners, research, prior tools, datasets, and platform documentation. It cannot exhaust the internet. Current products and model availability can change. We have not reproduced research results, surveyed customers, run the selected model, or established market novelty. Those limitations are reflected in the PRD's scope and gates.

## 7. Decision record

- **Recommended project:** Second Look, working title.
- **Track:** Best Apps and Agents.
- **MVP focus:** feature availability and temporal evaluation-policy mismatch in supported tabular experiments.
- **Technology:** Nemotron on Nebius Token Factory, deterministic Python/scikit-learn runner, React/TypeScript interface.
- **No mandatory extra prize integration:** Tavily is not part of the core job.
- **Critical proof:** two schemas, consequential model decisions, evidence-backed correction, a clean case left alone, an ambiguous case that remains unresolved, and reproducible execution.
- **First build gate:** prove that loop on development cases within the first two sessions. A failed gate triggers scope revision, not inflated claims.
- **Next documents:** [Product requirements](PROJECT_PRD.md) and [delivery/evaluation plan](DELIVERY_AND_EVALUATION_PLAN.md).

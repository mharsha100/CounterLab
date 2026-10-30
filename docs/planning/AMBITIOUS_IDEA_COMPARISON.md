# The ambitious choice: CounterLab

**Decision date: October 16, 2026. Research and specification only; nothing has been built or experimentally validated.**

## 1. Decision

**Recommend CounterLab: an AI investigator that converts scientific disagreement into discriminating experiments and reproducible, conditional conclusions.** Working tagline: **Turn disagreement into experiments.**

This is my highest-ceiling recommendation among the directions examined. There is no defensible way to establish the single strongest imaginable idea, and no research can guarantee a hackathon result. The recommendation is a product judgment with explicit tests that could prove it wrong.

I removed laptop limits, development time, and compute cost from the initial comparison of the visions. CounterLab wins that comparison in my judgment because the difficulty of deciding what evidence would distinguish competing explanations grows as AI makes research outputs cheaper to produce. A system that improves that decision could serve many computational research fields. This is a hypothesis about potential value, not measured demand or a claim that it has greater social value than every robotics or scientific discovery project.

The October 30 submission remains subject to a real deadline. Its requirements below preserve the defining scientific loop; they do not promise the entire long-term vision in two weeks.

## 2. What the unrestricted vision actually does

A researcher supplies competing empirical claims, relevant papers, code, and data. CounterLab:

1. Extracts the exact quantity each claim concerns, its assumptions, and the evidence cited.
2. Separates genuine disagreement from different populations, metrics, implementations, or experimental conditions.
3. Forms competing explanations and writes down what each predicts under a proposed intervention.
4. Chooses a useful experiment whose possible outcomes distinguish those explanations.
5. Commits the protocol, budget, stopping rule, and interpretation before inspecting results.
6. Executes controlled experiments in isolated environments, checks the implementation, and revises the investigation when evidence warrants it.
7. Makes a map of the tested conditions: which explanation is supported, which is contradicted, where both are compatible, and where evidence is insufficient.
8. Produces a replayable research record containing unsuccessful attempts as well as successful ones.

With substantial resources, this could grow into a research infrastructure spanning computational ML, optimization, simulation, and eventually instrument-connected laboratories with domain oversight. General paper-to-code execution, formal proof assistance, multi-institution replication, and physical experiments are future capabilities. They are not hackathon promises.

The demanding part is **selecting an experiment that changes what can reasonably be concluded**. More agents, more GPUs, a literature summary, or an attractive result dashboard do not establish that capability.

## 3. The strongest alternatives considered

| Direction, considered at full ambition | Highest-value outcome | Existing work and unresolved gap | Decision |
| --- | --- | --- | --- |
| **CounterLab** | Help research teams distinguish competing explanations and locate the conditions under which results hold | Replication and automated experiment design already exist; comparative claim contracts, discriminating experiments, and a usable conditional evidence record must earn their value | Recommended; strongest combination of cross-domain potential and a testable product distinction |
| **Robot Failure Lab** | Discover dangerous policy failures, learn recovery behavior, and demonstrate improved safety and task success across robots | NVIDIA evaluation tools, adaptive failure search, and failure-driven policy updates already cover much of this loop; transfer to new tasks and real hardware would be decisive | Strongest alternative, particularly for visual demonstration; could outrank CounterLab if it proves transfer and CounterLab only produces summaries |
| **Flood response rehearsal agent** | Evaluate response staging and road-access interventions against flood scenarios | Operational products and research already exist; calibrated uncertainty, trustworthy local data, and decision-maker validation are crucial | High potential impact, but the distinct contribution is currently less clear |
| **Second Look, expanded** | Review experiment validity across notebooks, datasets, and deployment settings | Strong integrity tooling already exists; prediction-time semantics and accessible evidence can still make a useful product | Valuable, narrower job; retain as a separately specified alternative |

This is not a claim that the alternatives are weak. In particular, removing resource limits strengthens the robotics option substantially. CounterLab is selected for its proposed scientific decision workflow, not because robotics needs a larger GPU.

Robotics primary sources: [Isaac Lab-Arena](https://developer.nvidia.com/isaac/lab-arena), [Arena release discussion](https://github.com/isaac-sim/IsaacLab-Arena/discussions/1245), [RoboLab](https://research.nvidia.com/labs/srl/projects/robolab/), [ROBOGATE preprint](https://arxiv.org/abs/2603.22126), [FailBank preprint](https://arxiv.org/abs/2609.39820). Adaptive search in ROBOGATE's reported controller experiments must not be conflated with adaptive testing of every VLA it benchmarks. Its live site also flags evaluation qualification issues; its headline outcomes are not evidence for our proposed robot system.

Flood prior art: [FloodMapp products](https://www.floodmapp.com/products), [Esri response simulation case study](https://www.esri.com/en-us/lg/industry/government/ncdr-case-study), [2026 emergency-access research](https://doi.org/10.1016/j.ijdrr.2026.106053). These make the problem credible while raising the bar for differentiation.

## 4. Research that changes the decision

| Evidence | What it supports | What it does not support | Product consequence |
| --- | --- | --- | --- |
| [Hugging Face's ICML reproduction review](https://huggingface.co/blog/icml-2026-open-reproductions), organizer report, August 2026 | Large-scale agent-assisted reproduction generated opposing verdicts for 242 papers | Those are not 242 established scientific errors; automated verdicts and attempted reproduction are not verified truth | Compare protocols and inspect evidence before accepting a reported contradiction |
| [Many AI Analysts, One Dataset](https://arxiv.org/abs/2602.18710), 2026 preprint | Defensible analytical choices can produce different conclusions; model/persona choices can steer results | A particular aggregation method or our agent will recover a uniquely correct answer | Preserve analysis choices and report conditional outcomes; do not vote among agents |
| [Veritas](https://github.com/ChicagoHAI/veritas), public implementation | Paper/repository analysis, execution, fixes, claim checking, and reporting are already available | That our proposed comparison workflow is novel research | Benchmark against a serious replication baseline; explicitly investigate two protocols and competing predictions |
| [AI Scientist-v2](https://arxiv.org/abs/2504.08066), research paper and [code](https://github.com/SakanaAI/AI-Scientist-v2) | Automated research pipelines already include experiments and writeups | Broad scientific reliability or the novelty of adding a scientist agent | Avoid positioning as the first autonomous scientist |
| [LLM-AutoSciLab](https://scientific-discovery.github.io/llm-autoscilab-project/), author project page | Active experiment selection is already a research direction | Our experiment selector is algorithmically new or superior | Measure experiment selection against simple alternatives; product differentiation alone is not a research contribution |
| [FIRE-Bench](https://proceedings.mlr.press/v306/wang26d.html), ICML 2026 | Research reproduction can be evaluated against explicit task requirements | A broad benchmark result for our restricted adapters | Use precise reproducibility criteria; do not claim a benchmark score without running its actual protocol |

**Synthesis:** The defensible opportunity is a focused product workflow: take conflicting reports, make the differences inspectable, design a test that separates explanations, and return a conditional evidence map. Its originality and usefulness remain hypotheses until demonstrated.

## 5. What comparable winners actually tell us

There are no winners from this still-open edition. We examined organizer announcements from completed events. The earlier [research document](RESEARCH_AND_DECISION.md) records nine comparable winners and their sources. The new search also inspected NVIDIA's Cosmos Cookoff winners.

| Observed winner | Verified result/source | Useful observation | CounterLab implication |
| --- | --- | --- | --- |
| MediSimplifier; evaluation dashboard; Balagan | Nebius challenge first, second, third: [organizer announcement](https://nebius.com/blog/posts/serverless-ai-builders-challenge-winners) | Specific workflows, measurements, and visible technical tradeoffs feature prominently | Show a concrete research decision and the evidence behind it |
| Route Optimization Agent; OpenCodeReview | NVIDIA NeMo toolkit event first and second: [NVIDIA announcement](https://developer.nvidia.com/blog/hackathon-winners-bring-agentic-ai-to-life-with-the-nvidia-nemo-agent-toolkit/) | Sponsor tools contribute to observable actions | Nemotron must choose and revise experiments, with runtime evidence |
| Project Blackbox | DataHub grand prize; solo project: [organizer announcement](https://datahub.com/blog/meet-the-winners-of-build-with-datahub-the-agent-hackathon/), [entry](https://devpost.com/software/project-blackbox) | Investigation, intervention, verification, and recorded evidence form a coherent product | Complete the scientific loop instead of accumulating disconnected features |
| See How It Thinks; ResQ-AI; Voice Controlled AI Video Intelligence | Cosmos Cookoff first, second, third: [NVIDIA announcement](https://forums.developer.nvidia.com/t/the-results-are-in-meet-the-nvidia-cosmos-cookoff-winners-see-them-live-on-april-16/366130) | Physical and visual workflows can be highly legible in a demo | Give CounterLab an equally clear before/experiment/after story |

These are observations from a selected, promotional sample. We do not have score sheets, a matched sample of losing entries, or evidence that one feature caused a win. The Cosmos competition's topic also favors physical AI; its results do not establish a robotics advantage in this four-track event.

The useful inference is to make the audience, action, evidence, and outcome easy to see. It is not to copy the winners or assume a large vision compensates for an unreliable product.

## 6. Fair comparison with Second Look

### Compare visions at the same level

Second Look's expanded vision is an experiment integrity platform: understand the intended task, inspect the procedure, identify invalid assumptions, and produce defensible revisions. CounterLab's expanded vision is a scientific investigation platform: determine why claims differ, choose discriminating experiments, and establish the tested boundaries of competing explanations.

CounterLab has a broader scientific decision surface. Second Look has a more immediately understandable user promise. Neither owns an uncontested research category.

### Compare the proposed submissions at the same level

| Dimension | Second Look as specified | CounterLab as specified | Judgment |
| --- | --- | --- | --- |
| User question | Does my experiment support my intended prediction claim? | What experiment would explain these conflicting results? | CounterLab asks the more ambitious question |
| Core evidence | Feature timing, split policy, fixed model reruns | Source-linked protocol differences, competing predictions, controlled intervention, follow-up run | CounterLab has greater scientific depth if the experiment is genuinely discriminating |
| Demonstration | Suspicious score → evidence → approved correction → revised claim | Conflicting reports → test plan → measured outcome → updated explanation → tested condition map | CounterLab has greater narrative upside; Second Look is easier to explain |
| Technological implementation | Semantic tool choice plus deterministic checks | Semantic alignment, experimental planning, evidence-dependent replanning, reproducible execution | CounterLab can demonstrate more consequential Nemotron use; complexity alone earns nothing |
| Design | Clear guided flow for AI learners | Research vocabulary needs a simple decision-focused interface | Second Look starts with an advantage; CounterLab must earn clarity |
| Potential impact | Better small ML experiments and more defensible handoffs | Better decisions about conflicting computational research | CounterLab's ceiling is higher in our judgment; neither has validated product demand |
| Idea quality | Stronger than a generic leakage checker, but substantial prior art | A focused comparative investigation workflow, also surrounded by strong prior art | Conditional advantage to CounterLab; no first-of-kind claim |
| Evidence of generality | Two public datasets and contract variants | A real literature-linked experiment, a second case, and withheld diagnostic variants | Neither may advertise universal research coverage |
| Delivery confidence | Better specified and lower uncertainty | Real adapter fidelity and the agent's experiment choices are unproven | Second Look is currently the safer submission |

The four official criteria are equally weighted. This table contains reasoned judgments, **not invented judge scores or winning probabilities**. See [official judging guidance](https://nebiusglobalaihackathon.devpost.com/updates/46204-here-s-how-judging-works).

## 7. The real demonstration to pursue

The first candidate is the ICML paper [Towards Optimal Robustness in Learning-Augmented Paging](https://proceedings.mlr.press/v306/chen26gt.html). A [supporting reproduction protocol](https://huggingface.co/datasets/MarxistLeninist/repro-la-paging-bundle/blob/main/protocol.md) and a [challenging reproduction](https://huggingface.co/spaces/Auenchanters/repro-towards-optimal-robustness-in-learning-augmented-paging/blob/6a812dfa91a7c2c42167065a6c2340e7d04f4216/pages/claim-2-the-proposed-framework-achieves-the-best-possible-robustness-for-learning-augmented-paging-of-h-k-o-1-using-a-relative-prediction-budget-primitive/page.md) investigate different regimes. The challenge also audits a proof branch. We cannot assume scale alone explains their disagreement.

CounterLab would compare the algorithm, request generator, prediction corruption, cost denominator, cache size, and repetition scheme; propose a common controlled protocol; run an independently implemented adapter; and distinguish a measured finite-regime result from a theorem claim. If the protocols cannot be aligned, that limitation remains visible. A finite sweep does not prove or disprove an asymptotic theorem.

The secondary case examines evaluation-token accounting in [Do Transformers Need Three Projections?](https://arxiv.org/abs/2606.04032) and its [independent audit](https://huggingface.co/spaces/stresearch-dev/63430). The [MIT-licensed code](https://github.com/Brainchip-Inc/Do-Transformers-Need-3-Projections) permits inspection of EOS padding and loss masking. A paired evaluation can isolate the effect of counting padding tokens while holding the checkpoint and real text fixed. However, the [later public checkpoint](https://huggingface.co/BrainChip-AI/qkv-fineweb-300m) uses different data and corrected loss masking and lacks a matched baseline. It supports a mechanism demonstration, not adjudication of the original architecture comparison. This case cannot satisfy the core investigation gate without original paired artifacts or a faithful matched reproduction.

Both are previously reported issues. Reproducing them validates our workflow, not a claim that we discovered new science. Neither experiment has been run by us yet. Licensing and adapter fidelity are explicit first-build gates.

## 8. Decision conditions

Proceed with CounterLab as the ambitious recommendation, with the [new PRD](../../COUNTERLAB_PRD.md) and [delivery plan](../../COUNTERLAB_DELIVERY_PLAN.md). It must demonstrate:

- A real source-linked disagreement with a controlled experiment separating its competing explanations, backed by protocol and implementation fidelity. A standalone scoring-mechanism demonstration is insufficient.
- A committed prediction and protocol before the run.
- Evidence that changes or narrows the explanation, followed by an appropriate next test or justified stop.
- Reproduction from the exported record and a legitimate inconclusive outcome.
- Better decisions or more efficient useful testing than simple baselines under a declared budget.

If it only summarizes reports or follows a scripted reveal, it has not surpassed Second Look. If the experiment engine works but baselines match its quality, report that result and narrow the value claim. Retain Second Look as a distinct fallback; do not rename its original leakage demo and call the larger vision achieved.

The local RTX 4070 Laptop GPU was read as 8,188 MiB VRAM. This informs later execution choices, not the selection of the vision. Nemotron inference will use Nebius Token Factory; larger experiments may require separate cloud compute. No compute has been provisioned or purchased.

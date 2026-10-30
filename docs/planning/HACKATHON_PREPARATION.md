# Nebius x NVIDIA Global AI Hackathon — preparation brief

Verified against the live sources on **October 14, 2026**. This brief covers preparation only. It does not select a track, propose a project, or start an entry.

**October 15 phase update:** The user subsequently requested project research and a PRD. The new [planning package](../../START_HERE.md) recommends Second Look for Best Apps and Agents. Statements below about leaving the idea/track undecided describe the earlier preparation phase. Setup and implementation remain pending.

## 1. Where we stand

- Entrant: one person in the United States; intermediate AI development experience; a few hours available each day. The entrant confirmed no attendance at a listed Builders & Brews event.
- Devpost and Nebius accounts: **not yet created**. Credits and API access: **not yet verified**.
- Local tools found: Git, Python 3.13, Node.js 22, npm, and Docker CLI. GitHub CLI and FFmpeg were not found; neither is required to begin preparation. This directory is a planning folder, not a Git repository or hackathon project.
- Formal eligibility still needs the entrant's own check of legal age and the conflict restrictions in the [Official Rules](https://nebiusglobalaihackathon.devpost.com/rules). AI assistance is explicitly encouraged in an [organizer update](https://nebiusglobalaihackathon.devpost.com/updates/46205-how-to-build-a-winning-project); the human remains the solo entrant and must own the submitted work.

## 2. Non-negotiable facts

| Item | Verified requirement |
| --- | --- |
| Submission deadline | **Friday, October 30, 2026, 10:00 a.m. PDT = 1:00 p.m. EDT.** Aim to submit earlier. |
| Core technology | A working app must make a **runtime Nebius Token Factory inference API call** or run on **Nebius AI Cloud compute** (Serverless Jobs, Serverless Endpoints, or DevPods), **and** use at least one NVIDIA open source model. Calling the model only through another provider does not qualify. |
| Track | Select one of Coding and Agentic Engineering, Best Apps and Agents, Personal AI, or Physical AI when submitting. Do not choose one during this preparation phase. |
| Stage 1 | Pass/fail: baseline viability, real fit to the chosen track, and genuine application of the required platform. |
| Stage 2 | Four equally weighted 1–5 scores: technological implementation, design, potential impact, and quality of the idea. Technical implementation is the first tie breaker. |
| Judging | December 1–15, 2026; winners expected around January 11, 2027. The working demo must remain accessible free of charge through the judging period. Judges may score from the writeup, images, and video without trying the demo. |

Sources: [Official Rules](https://nebiusglobalaihackathon.devpost.com/rules), [FAQ](https://nebiusglobalaihackathon.devpost.com/details/faqs), and [judging update](https://nebiusglobalaihackathon.devpost.com/updates/46204-here-s-how-judging-works).

The [track descriptions in the rules](https://nebiusglobalaihackathon.devpost.com/rules) add context beyond the universal platform/model baseline. **Coding and Agentic Engineering** concerns agents that write, run, and test code in Token Factory. **Best Apps and Agents** explicitly calls for Nemotron on Token Factory; Serverless Endpoints/Jobs are encouraged but not mandatory. **Personal AI** concerns a private, persistent assistant with memory, skills, tools, and action; the named supporting tools are examples. **Physical AI** concerns embodied or edge systems; the [FAQ](https://nebiusglobalaihackathon.devpost.com/details/faqs) permits simulation without a robot. These are definitions to understand, not a track choice or project direction.

### Submission assets to know now

Later, the entry needs a working demonstration URL (except the Physical AI exception), a clear English description, one track, a **public** GitHub/GitLab/Bitbucket repository with all required source/assets and a visible open source license, a README with setup and running instructions, and a **public YouTube video strictly under three minutes**. Include specific feedback about the Nebius and NVIDIA tools/models actually used. If adapting an older project, explain the significant work done during the submission period. The demo and repository must be usable for judging, with credentials supplied if a private app needs them. For Physical AI, the video needs at least one minute of real hardware operating, or, for a project without hardware, the key application modules in action. See the [Rules, Project and Submission Requirements](https://nebiusglobalaihackathon.devpost.com/rules).

### Awards relevant to planning

- Overall: $20,000 grand prize, $10,000 second, $6,000 third.
- One track winner in each of four tracks: NVIDIA Jetson Orin Nano.
- Best Use of Tavily: $3,000, only if the project makes a functional runtime Tavily API call.
- Most Valuable Feedback: ten awards of $100 plus NVIDIA swag; feedback is still required for every entry.
- One project may receive **one overall award OR one track award plus one bonus award**, per the [Rules](https://nebiusglobalaihackathon.devpost.com/rules).
- **City Winner is unavailable on the facts supplied:** the entrant did not attend a listed in-person event, and the supplied event schedule ended October 13. The pasted resource description says attendance is optional, but the current [Rules](https://nebiusglobalaihackathon.devpost.com/rules) and [FAQ](https://nebiusglobalaihackathon.devpost.com/details/faqs) explicitly require it.

## 3. What the competitor numbers actually tell us

Devpost currently shows roughly **23,100 registered participants**. The supplied filters show 10,678 people marked working solo, 8,909 full-stack developers, 2,480 data scientists, 10,877 listing Python, and 2,170 listing machine learning. Those labels are self reported and overlapping. They do not count submitted projects, eligible entries, or skill level. Likewise, the 91-person “AI Engineer” tag does **not** imply that only 91 entrants can build AI. The [project gallery](https://nebiusglobalaihackathon.devpost.com/project-gallery) is not published, so there is no verified completed-submission count or defensible win probability. Solo participation is common; it is not a disqualifier. The judging rubric, rather than these tags, is the useful benchmark. Sources: [participant page](https://nebiusglobalaihackathon.devpost.com/participants), [gallery](https://nebiusglobalaihackathon.devpost.com/project-gallery), [Rules](https://nebiusglobalaihackathon.devpost.com/rules).

## 4. The shortest preparation path

There are only **16 calendar days** between October 14 and the deadline. With a few hours a day, preparation should be a short access-and-skill sprint. Spending most of the remaining time studying would leave too little time to make and package a competitive entry. These dates are our planning targets, not official deadlines.

| When | Preparation task | Proof of readiness |
| --- | --- | --- |
| Oct 14 | Read this brief and the FAQ/rules; verify age and conflict eligibility; create/login to Devpost and click **Join Hackathon**. | Devpost shows membership in the hackathon; eligibility self-check complete. |
| Oct 14–15 | Join the [Nebius Builder Program](https://dev.nebius.com/builders), verify email, use the [hackathon promo form](https://nebius.com/promo-code?utm_promo_event_code=2026-devpost-global-ai-hack&utm_promo_code_type=Token_Factory&utm_promo_activation_code=NEBIUS-DEVPOST-GLOBAL26) with code `NEBIUS-DEVPOST-GLOBAL26`, and create Token Factory access. | Credits visible in transactions, or a concrete support issue logged. |
| Oct 15 | Read [Token Factory quickstart](https://docs.tokenfactory.nebius.com/quickstart), [current billing guide](https://docs.tokenfactory.nebius.com/other-capabilities/billing-new), and [NVIDIA model listing](https://nebius.com/services/token-factory/models/nvidia-nemotron-models-inference). | Can explain API key storage, billing behavior, required runtime path, and how to find a live NVIDIA model ID. |
| Oct 15–16 | Make one **neutral hello-world API call** to an available NVIDIA model through Token Factory, solely to test access; inspect exact model ID, response, usage, latency, and rate limits. This is a platform exercise, not an entry. | Successful call and observations recorded without exposing the key. |
| Oct 16 | Study the [40-minute organizer build session](https://nebiusglobalaihackathon.devpost.com/updates/46337-build-session-recording-resources-available-live-coding-your-first-app-with-nebius) and the [winning-project guidance](https://nebiusglobalaihackathon.devpost.com/updates/46205-how-to-build-a-winning-project). | Can explain the four judging dimensions and a clear three-minute demonstration structure without borrowing a project concept. |
| Oct 16–17 | Recheck account balance, quotas, and platform availability; record what is known and unresolved. | Preparation checklist below is complete enough to begin the next phase. |

**Decision gate:** target the end of October 16 or 17 for finishing preparation. The next phase, only when you explicitly want it, is project direction and build. No direction is chosen here.

## 5. Accounts, credits, and spending

1. Join the [Devpost hackathon](https://nebiusglobalaihackathon.devpost.com/) so updates and entry tools are available.
2. The organizer advertises **$25 Token Factory credits** from the [promo form](https://nebius.com/promo-code?utm_promo_event_code=2026-devpost-global-ai-hack&utm_promo_code_type=Token_Factory&utm_promo_activation_code=NEBIUS-DEVPOST-GLOBAL26) and another **$25 Token Factory credits** through the [Builder Program](https://dev.nebius.com/builders). Verify each grant in the account; do not assume the balance until it appears. The [FAQ](https://nebiusglobalaihackathon.devpost.com/details/faqs) says there is no separate published AI Cloud credit grant.
3. Read the live billing screen before entering a card. The [current Token Factory billing guide](https://docs.tokenfactory.nebius.com/other-capabilities/billing-new) says onboarding requires a bank card, grants $1 trial credit for 30 days, and may automatically charge the card under its billing policy. An [older billing page](https://docs.tokenfactory.nebius.com/other-capabilities/billing) differs on the card requirement. The live account flow decides what you actually must do. Review any threshold and account consumption after the credits are applied.
   The [hackathon rules](https://nebiusglobalaihackathon.devpost.com/rules) state that no purchase or payment is necessary to enter. If the card requirement blocks access, raise it with the organizer promptly rather than assuming an unofficial workaround.
4. Create an API key only after account setup. Keep `NEBIUS_API_KEY` private; never paste it into chat or commit it. The [quickstart](https://docs.tokenfactory.nebius.com/quickstart) uses an OpenAI-compatible API at `https://api.tokenfactory.nebius.com/v1/`. Its sample uses a non-NVIDIA model, so choose a live NVIDIA model ID from the account catalog for the eligibility access test.
5. Nebius AI Cloud Serverless compute has its own [pricing and quotas](https://docs.nebius.com/serverless/pricing-quotas). Token Factory promo credits do not cover it, per the FAQ. Avoid provisioning Cloud compute until costs and actual access are clear.
6. If credits or country provisioning fail, the [FAQ](https://nebiusglobalaihackathon.devpost.com/details/faqs) directs entrants to the [Nebius Discord](https://discord.gg/eXYTGhgnhK). Record the issue, exact page, and time for later feedback.

## 6. What a strong entry will have to prove later

This is a judge-facing evidence standard, not a project concept. The [organizers' judging guidance](https://nebiusglobalaihackathon.devpost.com/updates/46204-here-s-how-judging-works) favors meaningful, complete behavior over thin wrappers. Because judges may judge from media alone, the later submission should make each criterion observable quickly.

| Equal-weight criterion | Evidence to preserve during the later build |
| --- | --- |
| Technological implementation | A genuine Nebius runtime call or deployment; an exact NVIDIA model ID; an authentic end-to-end run; tests or checks for core behavior; measured latency, usage, and failure handling. |
| Design | A coherent start-to-finish flow, understandable controls and states, readable output, and behavior that matches the video. |
| Potential impact | A specific audience and problem, credible evidence the problem exists, a before/after result or other concrete outcome, and limits stated honestly. |
| Quality of the idea | A clear explanation of the distinctive insight, why the chosen technology belongs in the solution, and why the work fits its selected track. |

When an entry exists, the public video should be a **pitch plus working proof**, not a long setup tutorial: open with the problem and audience, show the real workflow, explain the Nebius/NVIDIA roles aloud, and end with the verified result. Leave margin under the three-minute limit. The [organizer's submission advice](https://nebiusglobalaihackathon.devpost.com/updates/46205-how-to-build-a-winning-project) specifically emphasizes naming the tools in the description, Built With section, and narration.

## 7. Skills to master without starting an entry

Use short, generic exercises. Stop once you can repeat each result and explain it clearly.

| Skill | Preparation proof |
| --- | --- |
| Platform mechanics | Explain the difference between a Token Factory inference call and AI Cloud compute, and which one satisfies the rules. |
| Model access | Locate the live NVIDIA model ID, model card, license, context limit, tool/JSON support, and price before relying on it. The catalog may change. |
| API use | Make a neutral request, handle authentication and a failed request, observe latency/token usage, and read the [rate limits](https://docs.tokenfactory.nebius.com/ai-models-inference/rate-limits). |
| Cost control | Read the live balance, transactions, and consumption view; know what can auto-charge. |
| Reproducibility | Explain how a fresh reviewer would run a repository from a README and where a secret must never appear. |
| Evidence | For any later feature, preserve one authentic end-to-end run, a known failure, and a measurable improvement. |
| Communication | Practice a neutral three-minute explanation with problem, audience, live behavior, why Nebius and NVIDIA matter, and what was actually verified. |
| Feedback | Record tool/model name, purpose, onboarding steps, what worked, specific failure and reproduction, cost/latency observations, and whether you would use it again. |

For background only, the NVIDIA model families named by the organizers include [Nemotron](https://nebius.com/services/token-factory/models/nvidia-nemotron-models-inference), [GR00T](https://developer.nvidia.com/isaac/gr00t), [Cosmos](https://docs.nvidia.com/cosmos/latest/introduction.html), and [GEAR-SONIC](https://github.com/NVlabs/GR00T-WholeBodyControl). Their access, licensing, and compute needs differ sharply. The [FAQ](https://nebiusglobalaihackathon.devpost.com/details/faqs) allows simulation for Physical AI. No model family or track is selected here.

## 8. Risks to resolve before committing to a direction

- **Access:** the account, credits, and actual NVIDIA endpoint have not yet been tested.
- **Budget:** card and automatic-charge behavior need the entrant's review before use; Token Factory credits do not fund AI Cloud.
- **Rules ambiguity:** Coding-track wording about writing/running/testing code “in Token Factory” has not been clarified as a Sandboxes requirement. If that track later becomes relevant, obtain a written organizer answer in the [discussion thread](https://nebiusglobalaihackathon.devpost.com/forum_topics/45140-clarifications-submissions-award-stacking-and-tavily-credit-access).
- **Evidence:** judges may not open the app. Later, the writeup/video must stand on their own and clearly show the actual NVIDIA model and Nebius runtime path.
- **Timing:** reserve time before October 30 for a public repository, rights/secret check, public YouTube upload, and a complete Devpost submission. The [latest update](https://nebiusglobalaihackathon.devpost.com/updates/46206-did-someone-say-prizes) urges early submission because uploads and debugging take longer than expected; it does not promise early organizer review.

## 9. Working together

You control the accounts, eligibility declaration, billing choice, and final submission. I will maintain the rules/source checks, help troubleshoot the neutral platform test, keep the readiness log clear, and later review a project against all four judging criteria once you decide to enter the next phase. This preserves your solo entrant status and your ownership of the work.

See [READINESS_TRACKER.md](../../READINESS_TRACKER.md) for the live checklist and observation log.

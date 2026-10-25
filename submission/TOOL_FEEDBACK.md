# Tool feedback — submission draft

## Nebius Token Factory

**Use:** Runtime OpenAI-compatible requests to NVIDIA Nemotron for bounded
experiment selection and structured predictions. Exact requested and returned
model IDs, usage, response finish reasons and failures are preserved.

**What worked:** A text probe and a tool/structured-output probe passed. The
application integrated through a small backend transport; saved usage and
response metadata made the later evaluation auditable. Promotional credit
redemption worked after receiving the separate email code.

**What needs work:** An early source investigation returned arguments outside
the allowed schema. Super-VL development probes exhausted 4,096 and 8,192 output
tokens, predominantly on reported reasoning, without a usable completed plan.
These are specific probe outcomes, not a capability ranking. More explicit
model-specific guidance on reasoning/output allowances and structured-output
failure handling would shorten onboarding. Responses require validation and
bounded failure handling in the client.

**Onboarding:** Account, promotional form/email redemption, backend environment
key, exact model-ID discovery, text probe, then a tool/structured-output probe.
The Builders Program's extra credit arrived separately. These steps should be
clear in one getting-started guide. No exact onboarding duration was measured.

**Would use again:** Yes, for hosted open-model experiments with explicit budgets
and recorded metadata. Production selection would require a broader benchmark,
latency/cost measurements and stronger evidence than the current development set.

## NVIDIA Nemotron

**Use:** `nvidia/Nemotron-3-Ultra-550b-a55b` proposed experiments and committed
predictions in the source workflow and frozen evaluation. Earlier Lightning and
Super-VL probes tested connection/structured-output behavior; they were not a
general model comparison.

**What worked:** Ultra produced usable structured plans and some discriminating
tests. The adaptive policy found both available finite differences in the latest
source set. Real returned model identifiers are retained in the records.

**What needs work:** Prediction accuracy was low: both predictions matched on
2/11 measured adaptive tests. The heuristic also found both differences with
zero model calls. Some replies violated necessary input conditions; two fixed
policy tasks retained truncated first replies. We added deterministic checks
and factual reporting. The new prediction guard is not yet live-model evaluated.

**Would use again:** Yes, as an experiment proposer whose claims are checked by
execution. The evidence does not support autonomous scientific adjudication or
claiming this is the best model for all research tasks.

## Other services

Nebius AI Cloud and Serverless compute were not used; numerical execution ran
locally in restricted Docker containers. Tavily and the other partner benefits
were not used. No performance or onboarding feedback is claimed for those tools.

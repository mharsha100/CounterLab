# Tool feedback — submission draft

## Nebius Token Factory

**Use:** Runtime OpenAI-compatible requests to NVIDIA Nemotron for bounded
experiment selection, structured predictions, open experiment design, harness generation,
repair and measured-result follow-up. Exact requested and returned
model IDs, usage, response finish reasons and failures are preserved.

**What worked:** A text probe and a tool/structured-output probe passed. The
application integrated through a small backend transport; saved usage and
response metadata made the later evaluation auditable. Promotional credit
redemption worked after receiving the separate email code. In the first live
open investigation (October 30), Token Factory accepted a large strict
`json_schema` response format for Nemotron 3 Ultra on every request (no fallback
needed): two ~6,000-output-token designs in about 21 seconds each and a repair in
4 seconds, with no 429s or retries.

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

**Specific, reproducible documentation issues (rechecked October 27, 2026):**

1. [Structured output & JSON](https://docs.tokenfactory.nebius.com/ai-models-inference/json.md):
   the Python `json_schema` example has no comma between `"type": "json_schema"`
   and `"json_schema": Film.model_json_schema()`, so it raises a `SyntaxError`
   when copied. The cURL example spells the key `"response format"` (with a
   space) instead of `response_format`, so the schema is not applied.
2. The same page does not say how reasoning models interact with `json_schema`
   and `max_tokens`. With Nemotron reasoning on by default, hidden reasoning
   tokens count against `max_tokens`; our Super-VL probes exhausted 4,096 and
   8,192 tokens before emitting a plan (`finish_reason: "length"`). One sentence
   recommending an allowance, or a link to the per-model reasoning switch, would
   have saved those paid probes.
3. [Rate limits](https://docs.tokenfactory.nebius.com/ai-models-inference/rate-limits.md)
   documents the `Retry-After` and `x-ratelimit-*` headers well, but not which
   other HTTP codes clients should expect (for example credit exhaustion
   versus model access). We map 401/402/403/404/429 to fixed user-facing
   actions ourselves; an official table would make that consistent.
4. The [November 2026 deprecation notice](https://docs.tokenfactory.nebius.com/model-deprecations-november-2026.md)
   removes `nvidia/nemotron-3-super-120b-a12b` and `NVIDIA-Nemotron-3-Nano-30B-A3B`
   from serverless on November 9, inside the period when hackathon demos must
   stay working (the current judging period runs December 9–23). Requests are not rerouted. A
   direct notice to hackathon participants would prevent silent demo failures.
   `Nemotron-3-Ultra-550b-a55b`, which CounterLab uses, is not on the list.

## NVIDIA Nemotron

**Use:** `nvidia/Nemotron-3-Ultra-550b-a55b` designs Open Lab experiments,
commits explanations and bets, writes and repairs harnesses, and designs a follow-up
from measured results. It also proposed experiments and committed predictions in
the earlier paging case study and frozen evaluation. Earlier Lightning and
Super-VL probes tested connection/structured-output behavior; they were not a
general model comparison.

**What worked:** Ultra produced usable structured plans and some discriminating
tests. The adaptive policy found both available finite differences in the latest
source set. Real returned model identifiers are retained in the records. In the October 30
Open Lab run, Ultra generated two experiment designs and repaired its failing
follow-up harness from the recorded traceback. That run completed in 87 seconds
with three model calls and 23,005 reported tokens; both admitted experiments
matched their repeat execution.

**What needs work:** Prediction accuracy was low: both predictions matched on
2/11 measured adaptive tests. The heuristic also found both differences with
zero model calls. Some replies violated necessary input conditions; two fixed
policy tasks retained truncated first replies. We added deterministic checks
and factual reporting. The case-study prediction guard has not been evaluated on a new live-model
benchmark. Open Lab has one recorded live investigation: its first bet failed,
then its follow-up harness needed repair. Its repaired follow-up bet held, but
one example does not establish general scientific reliability.

**Onboarding:** We accessed the hosted models through the existing Nebius backend
connection, using exact model IDs. A Lightning connection/tool probe preceded
Ultra and Super-VL development cases. We then separated schema validation,
prediction correctness and output-budget failures rather than treating a
successful API response as a successful investigation. We did not install local
NVIDIA model weights or measure a separate NVIDIA onboarding duration.

**Would use again:** Yes, as an experiment proposer whose claims are checked by
execution. The evidence does not support autonomous scientific adjudication or
claiming this is the best model for all research tasks.

## Other services

Nebius AI Cloud and Serverless compute were not used; numerical execution ran
locally in restricted Docker containers. Tavily and the other partner benefits
were not used. No performance or onboarding feedback is claimed for those tools.

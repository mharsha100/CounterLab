// Shared wording helpers. Codes come from the backend; the browser never sees
// provider messages, request bodies or credentials, only these fixed codes.

export function plural(count: number, singular: string, pluralForm = `${singular}s`): string {
  return `${count.toLocaleString('en-US')} ${count === 1 ? singular : pluralForm}`;
}

const httpActions: Record<number, string> = {
  400: 'Nebius rejected the request format. The saved request is kept for inspection.',
  401: 'Nebius did not accept the API key. Replace it in Settings (it is stored as NEBIUS_API_KEY in your local .env file).',
  402: 'Nebius reported a billing or credit problem. Review your Token Factory balance before starting again.',
  403: 'This key cannot use the requested model or operation. Check model access in Token Factory.',
  404: 'Nebius could not find the model or route. Confirm the exact model ID in your account catalog.',
  408: 'The Nebius request timed out, including the automatic retry. Wait a moment, then run it again.',
  429: 'Nebius kept rate-limiting the request, even after the automatic retries. Wait about a minute, then run it again.',
};

const reasons: Record<string, string> = {
  model_not_in_catalog: 'No NVIDIA Nemotron model is available in your Token Factory catalog. Open Settings → Check connection to see what your key can use.',
  no_nemotron_model_in_catalog: 'No NVIDIA Nemotron model is available in your Token Factory catalog. Check that your key belongs to the right Token Factory project.',
  provider_timeout: 'Nebius did not answer in time, even after one automatic retry. Run it again in a moment.',
  provider_response_invalid: 'Nebius returned an unreadable response, even after the automatic retries. Run it again in a moment.',
  provider_retry_limit_reached: 'Nebius stayed unavailable after every automatic retry. Run it again in a few minutes.',
  probe_response_invalid: 'Nemotron answered, but not with the expected JSON. Investigations still validate every answer; try the test again.',
  cancelled_by_user: 'You stopped this investigation. Everything saved before that stays in the record.',
  provider_connection_error: 'CounterLab could not reach Nebius, even after the automatic retries. Check your internet connection, then run it again.',
  experiment_worker_failed: 'The isolated experiment worker stopped. Start Docker Desktop and run scripts/check_worker.py.',
  server_restarted: 'The app restarted while this run was in progress. Its saved steps are kept; start a new run to continue.',
  investigation_or_integrity_error: 'The run stopped during an integrity check. Its saved files are kept for inspection.',
  source_investigation_or_integrity_error: 'The run stopped during an integrity check. Its saved files are kept for inspection.',
  provider_error_no_retry: 'The Nebius request failed, so nothing was measured for that turn.',
  returned_model_mismatch: 'Nebius answered with a different model than requested, so the plan was not used.',
  incomplete_plan_not_retried: 'Nemotron stopped before finishing its plan (often its output limit). The partial answer is kept and was not executed.',
  incomplete_structured_plan_not_retried: 'Nemotron stopped before finishing its plan (often its output limit). The partial answer is kept and was not executed.',
  generation_budget_exhausted_not_a_reasoning_verdict: 'Nemotron used its whole output allowance before answering. This is a budget limit, not a judgement about its reasoning.',
  invalid_plan_not_executed: 'The returned plan did not match the required format, so it was not executed.',
  repeated_test_not_executed: 'Nemotron chose a test it had already tried, so it was not run again.',
  repeated_case_not_executed: 'Nemotron chose a case it had already tried, so it was not run again.',
  worker_or_measurement_failed_no_retry: 'An isolated measurement failed. Partial outputs are kept but are not treated as evidence.',
  transport_or_worker_error_no_retry: 'A provider or worker error stopped the run. Saved steps are kept; nothing was retried.',
  transport_or_internal_error_no_automatic_retry: 'A provider or internal error stopped the run. Saved steps are kept; nothing was retried.',
  measurement_or_contract_verification_failed: 'A measurement did not pass verification, so it was not used as evidence.',
  no_accepted_experiment_within_planning_limit: 'No admissible test was proposed within the planning limit. The rejected plans remain on the record.',
  inference_request_limit_reached: 'The run reached its model-request limit before finishing.',
  not_measured: 'Nemotron\u2019s experiment code could not be admitted or run within the repair limit, so nothing was measured. The checks below show why.',
  not_designed: 'Nemotron did not return a usable experiment design, so nothing was committed or run.',
  guard_rejected: 'CounterLab\u2019s guard rejected the committed plan before anything ran, so nothing was measured.',
  repair_failed: 'The experiment code could not be repaired within the limit, so nothing was measured.',
  sandbox_failed: 'The sandbox could not run the experiment, so nothing was measured.',
  needs_review: 'The experiment ran, but not every measurement completed or repeated exactly. Only reproduced comparisons are judged.',
  model_call_budget_exhausted: 'The run used all of its Nemotron requests before an experiment could be measured.',
  model_refused: 'Nemotron declined to answer, so nothing was committed or run.',
  output_allowance_exhausted: 'Nemotron used its whole output allowance before finishing a design. Try a larger allowance.',
  response_not_json: 'Nemotron\u2019s answer was not valid JSON, so it was not used.',
  plan_fields_do_not_match_schema: 'Nemotron\u2019s design did not match the required format, so it was not used.',
  open_investigation_error: 'The investigation stopped unexpectedly. Its saved steps are kept for inspection.',
  intake_error: 'The uploaded inputs could not be used.',
  sandbox_unavailable: 'The sandbox is not ready. Start Docker Desktop, then open Settings → Sandbox to set it up (or run scripts/setup_open_runner.py).',
};

export function failureMessage(code: string): string {
  const http = /^provider_http_(\d{3})$/.exec(code);
  if (http) {
    const status = Number(http[1]);
    return httpActions[status] ?? (status >= 500
      ? `Nebius returned a server error (HTTP ${status}) after the automatic retries. Wait a few minutes, then run it again.`
      : `Nebius stopped the request (HTTP ${status}). The saved request is kept for inspection.`);
  }
  if (Object.hasOwn(reasons, code)) return reasons[code];
  const readable = code.replaceAll('_', ' ').trim();
  return readable ? `${readable.charAt(0).toUpperCase()}${readable.slice(1)}.` : 'The run stopped.';
}

// Axis ticks on round steps (1, 2, 2.5 or 5 × 10^n) inside [low, high].
export function niceTicks(low: number, high: number, target: number): number[] {
  if (!(Number.isFinite(low) && Number.isFinite(high)) || high <= low || target < 1) return [];
  const raw = (high - low) / target;
  const magnitude = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map(factor => factor * magnitude).find(candidate => candidate >= raw * (1 - 1e-12)) ?? raw;
  const ticks: number[] = [];
  for (let index = Math.ceil(low / step - 1e-9); index * step <= high + step * 1e-9; index += 1) ticks.push(Number((index * step).toPrecision(12)));
  return ticks;
}

// A chart label on at most two lines of maxChars, broken at a space when possible.
export function wrapLabel(text: string, maxChars: number): string[] {
  const clip = (value: string) => value.length > maxChars ? `${value.slice(0, Math.max(1, maxChars - 1))}…` : value;
  if (text.length <= maxChars) return [text];
  const cut = text.lastIndexOf(' ', maxChars);
  if (cut <= 0) return [clip(text)];
  return [text.slice(0, cut), clip(text.slice(cut + 1))];
}

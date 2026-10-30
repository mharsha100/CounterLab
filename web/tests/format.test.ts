import assert from 'node:assert/strict';
import test from 'node:test';
import { failureMessage, niceTicks, plural, wrapLabel } from '../src/format.ts';

test('counts read naturally for one and many', () => {
  assert.equal(plural(1, 'measured test'), '1 measured test');
  assert.equal(plural(0, 'measured test'), '0 measured tests');
  assert.equal(plural(12345, 'event'), '12,345 events');
  assert.equal(plural(2, 'policy', 'policies'), '2 policies');
});

test('provider failures explain what happened and what to do next', () => {
  assert.match(failureMessage('provider_http_429'), /rate-limiting/i);
  assert.match(failureMessage('provider_http_429'), /automatic retries/);
  assert.match(failureMessage('provider_http_401'), /Settings/);
  assert.match(failureMessage('provider_timeout'), /retry/);
  assert.match(failureMessage('provider_http_503'), /HTTP 503/);
  assert.match(failureMessage('provider_http_418'), /HTTP 418/);
  assert.match(failureMessage('model_not_in_catalog'), /Check connection/);
});

test('unknown codes stay readable and never leak raw underscores', () => {
  assert.equal(failureMessage('some_new_reason'), 'Some new reason.');
  assert.equal(failureMessage(''), 'The run stopped.');
  assert.doesNotMatch(failureMessage('incomplete_plan_not_retried'), /_/);
  // Prototype keys are not treated as known reasons.
  assert.equal(failureMessage('constructor'), 'Constructor.');
});

test('open investigation stops say what to do next', () => {
  assert.match(failureMessage('sandbox_unavailable'), /setup_open_runner\.py/);
  assert.match(failureMessage('output_allowance_exhausted'), /larger allowance/);
  assert.match(failureMessage('not_measured'), /nothing was measured/);
  assert.doesNotMatch(failureMessage('model_call_budget_exhausted'), /_/);
});

test('chart ticks land on round values inside the range', () => {
  assert.deepEqual(niceTicks(0.79, 1.06, 5), [0.8, 0.9, 1]);
  assert.deepEqual(niceTicks(1490, 1730, 5), [1500, 1550, 1600, 1650, 1700]);
  assert.deepEqual(niceTicks(-3, 3, 3), [-2, 0, 2]);
  assert.deepEqual(niceTicks(1, 1, 5), []);
  assert.deepEqual(niceTicks(Number.NaN, 2, 5), []);
  for (const tick of niceTicks(0.9971, 1.0113, 5)) assert.ok(tick >= 0.9971 && tick <= 1.0113);
});

test('long chart labels wrap to two lines at a space, then clip', () => {
  assert.deepEqual(wrapLabel('Group A', 20), ['Group A']);
  assert.deepEqual(wrapLabel('Reproduction (refresh every request)', 30), ['Reproduction (refresh every', 'request)']);
  assert.deepEqual(wrapLabel('averyveryverylongidentifierwithoutspaces', 10), ['averyvery…']);
  for (const line of wrapLabel('one two three four five six seven eight nine ten', 12)) assert.ok(line.length <= 12);
});

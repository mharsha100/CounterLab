import assert from 'node:assert/strict';
import { test } from 'node:test';
import { recoverableResource } from '../src/recoverableResource.ts';

test('a transient failed read can be explicitly retried, without automatic requests', async () => {
  let calls = 0;
  const load = recoverableResource(async () => {
    calls++;
    if (calls === 1) throw new Error('temporary network failure');
    return { schema: 1 };
  });
  await assert.rejects(load(), /temporary network failure/);
  assert.equal(calls, 1);
  assert.deepEqual(await load(), { schema: 1 });
  assert.equal(calls, 2);
});

test('concurrent readers share the same successful request and cached value', async () => {
  let calls = 0;
  const load = recoverableResource(async () => { calls++; return { schema: 1 }; });
  const [a, b] = await Promise.all([load(), load()]);
  assert.equal(a, b);
  assert.equal(await load(), a);
  assert.equal(calls, 1);
});

test('concurrent failures share one read and later retry shares one new read', async () => {
  let calls = 0;
  const load = recoverableResource(async () => { calls++; throw new Error('unavailable'); });
  await Promise.all([assert.rejects(load(), /unavailable/), assert.rejects(load(), /unavailable/)]);
  assert.equal(calls, 1);
  await assert.rejects(load(), /unavailable/);
  assert.equal(calls, 2);
});

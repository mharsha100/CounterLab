import assert from 'node:assert/strict';
import { test } from 'node:test';
import { canonicalValue, commitPlan, settingsError, valueHash, type ProtocolTemplate, type WorkbenchSettings } from '../src/workbenchProtocol.ts';

const template: ProtocolTemplate = {version:'fixture_v1',scope:'human_designed_synthetic_diagnostic',
  counting_window:'cold',held_fixed:['requests','forecasts'],implementation_sha256:{'engine.py':'a'.repeat(64)}};
const settings: WorkbenchSettings = {family:'uniform',capacity:8,length:256,request_seed:0,algorithm_seed:0,
  forecast:'inverted',tau:1,predict_gate_difference:null,predict_miss_difference:null};

test('canonical UTF-8 bytes and fingerprint match the independently generated Python fixture', async () => {
  const value = {z:null,a:true,n:16,child:{beta:0,alpha:'cache'}};
  assert.equal(canonicalValue(value), '{"a":true,"child":{"alpha":"cache","beta":0},"n":16,"z":null}\n');
  assert.equal(await valueHash(value), '48b1c97ae3b738241bdee27b7b92be5c8f48a0be7ca42d2b09550973539dbc0a');
  assert.equal(canonicalValue({b:2,a:1}), canonicalValue({a:1,b:2}));
});

test('commitment snapshots settings and template instead of following later edits', async () => {
  const mutable = structuredClone(settings);
  const metadata = structuredClone(template);
  const plan = await commitPlan(metadata, mutable);
  mutable.capacity = 16;
  metadata.held_fixed.push('edited');
  assert.equal(plan.protocol.settings.capacity, 8);
  assert.deepEqual(plan.protocol.held_fixed, ['requests','forecasts']);
  assert.equal(plan.protocol_sha256, await valueHash(plan.protocol));
});

test('abstention and both prediction choices bind different plans', async () => {
  const hashes = await Promise.all([null,false,true].map(value=>commitPlan(template,{...settings,predict_gate_difference:value})));
  assert.equal(new Set(hashes.map(p=>p.protocol_sha256)).size, 3);
});

test('unsafe numbers and settings outside the Python contract cannot be committed', async () => {
  for (const invalid of [{...settings,capacity:0},{...settings,length:513},{...settings,algorithm_seed:4294967296},
    {...settings,request_seed:NaN},{...settings,tau:1.2},{...settings,family:'cyclic',request_seed:1},
    {...settings,family:'known_witness'},{...settings,forecast:'fixed_witness'}]) {
    assert.notEqual(settingsError(invalid as WorkbenchSettings), '');
    await assert.rejects(commitPlan(template, invalid as WorkbenchSettings));
  }
  assert.throws(()=>canonicalValue({number:Infinity}), /unsupported/);
});

import assert from 'node:assert/strict';
import { test } from 'node:test';
import { pathForRoute, routeFromSearch, routes, type Route } from '../src/navigationProtocol.ts';

test('every nested view round-trips through a portable project URL', () => {
  for (const route of Object.keys(routes) as Route[]) {
    const path = pathForRoute('https://example.test/CounterLab/?keep=yes#old', route);
    const restored = new URL(path, 'https://example.test');
    assert.equal(restored.pathname, '/CounterLab/');
    assert.equal(restored.searchParams.get('keep'), 'yes');
    assert.equal(restored.hash, '');
    assert.equal(routeFromSearch(restored.search), route);
  }
});

test('unknown and prototype property names fall back to the home view', () => {
  for (const query of ['', '?view=not-a-route', '?view=constructor', '?view=__proto__', '?view=https://other.test']) {
    assert.equal(routeFromSearch(query), 'home');
  }
  assert.throws(() => pathForRoute('https://example.test/', 'unknown' as Route));
});

test('back and forward URL restoration retains the intended subview', () => {
  const sequence: Route[] = ['demo', 'source-evaluation', 'experiment-workbench', 'source-investigator', 'selected-evidence'];
  const urls = sequence.map(route => pathForRoute('http://127.0.0.1:8000/', route));
  for (const index of [4, 3, 2, 1, 0, 1, 2, 3, 4]) {
    assert.equal(routeFromSearch(new URL(urls[index], 'http://127.0.0.1:8000').search), sequence[index]);
  }
});

test('view parameters are replaced, not carried into another view', () => {
  const run = pathForRoute('https://example.test/app/?view=runs&q=welford&status=completed&keep=yes', 'run', { id: 'a'.repeat(32), tab: 'e1' });
  const url = new URL(run, 'https://example.test');
  assert.equal(url.searchParams.get('view'), 'run');
  assert.equal(url.searchParams.get('id'), 'a'.repeat(32));
  assert.equal(url.searchParams.get('q'), null);
  assert.equal(url.searchParams.get('keep'), 'yes');
  const back = new URL(pathForRoute(url.href, 'runs'), 'https://example.test');
  assert.equal(back.searchParams.get('id'), null);
  assert.equal(back.searchParams.get('tab'), null);
});

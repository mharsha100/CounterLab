import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { test } from 'node:test';
import { MAX_ARCHIVE_BYTES, receiveArchive, validateFingerprint, verifyArchiveBytes } from '../src/archiveIntegrity.ts';

// Synthetic ZIP-signature fixture: tests byte validation, not extraction.
const fixture = new Uint8Array([0x50, 0x4b, 0x03, 0x04, 12, 19, 0, 1]);
const expected = { sha256: createHash('sha256').update(fixture).digest('hex'), bytes: fixture.length };
const response = (body: Uint8Array) => new Response(body, { headers: { 'Content-Type': 'application/zip' } });

test('complete streamed bytes match a separately computed checksum', async () => {
  const counts: number[] = [];
  const bytes = await receiveArchive(response(fixture), expected, n => counts.push(n), new AbortController().signal);
  assert.deepEqual(bytes, fixture);
  assert.equal(counts.at(-1), fixture.length);
  assert.equal(await verifyArchiveBytes(bytes, expected), expected.sha256);
});

test('same-size tampering fails checksum verification', async () => {
  const changed = Uint8Array.from(fixture);
  changed[5] ^= 1;
  await assert.rejects(verifyArchiveBytes(changed, expected), /checksum check failed/);
});

test('legitimate static-host ZIP MIME aliases retain all byte checks', async () => {
  for (const mime of ['application/x-zip-compressed', 'application/octet-stream']) {
    const bytes = await receiveArchive(new Response(fixture, {headers:{'Content-Type':mime}}), expected,
      () => {}, new AbortController().signal);
    assert.equal(await verifyArchiveBytes(bytes, expected), expected.sha256);
  }
});

test('truncated and oversized streams cannot become downloads', async () => {
  await assert.rejects(receiveArchive(response(fixture.slice(0, -1)), expected, () => {}, new AbortController().signal), /incomplete/);
  await assert.rejects(receiveArchive(response(new Uint8Array([...fixture, 1])), expected, () => {}, new AbortController().signal), /exceeds/);
});

test('HTML and wrong signatures are refused even with a matching checksum', async () => {
  await assert.rejects(receiveArchive(new Response('<html>error</html>'), expected, () => {}, new AbortController().signal), /ZIP archive/);
  const html = new TextEncoder().encode('<html>an error</html>');
  const metadata = { sha256: createHash('sha256').update(html).digest('hex'), bytes: html.length };
  await assert.rejects(verifyArchiveBytes(html, metadata), /not the expected ZIP/);
});

test('missing, invalid and excessive fingerprints fail before accepting data', () => {
  for (const value of [{ ...expected, sha256: '' }, { ...expected, bytes: 1.5 }, { ...expected, bytes: 0 },
    { ...expected, bytes: MAX_ARCHIVE_BYTES + 1 }, { ...expected, sha256: 'x'.repeat(64) }]) {
    assert.throws(() => validateFingerprint(value), /fingerprint/);
  }
});

test('HTTP errors and pre-cancelled downloads never return verified bytes', async () => {
  await assert.rejects(receiveArchive(new Response('bad', {status:409}), expected, () => {}, new AbortController().signal), /HTTP 409/);
  const abort = new AbortController();
  abort.abort();
  await assert.rejects(receiveArchive(response(fixture), expected, () => {}, abort.signal), {name:'AbortError'});
});

test('cancelling an active stream releases it and produces no partial artifact', async () => {
  let cancelled = false;
  const abort = new AbortController();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) { controller.enqueue(fixture.slice(0, 4)); },
    cancel() { cancelled = true; },
  });
  await assert.rejects(receiveArchive(new Response(stream, {headers:{'Content-Type':'application/zip'}}), expected,
    () => abort.abort(), abort.signal), {name:'AbortError'});
  assert.equal(cancelled, true);
});

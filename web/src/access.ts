// The evidence build has no backend or provider connection. Never fall back to
// the live API when a snapshot is missing or fails its integrity check.
import { receiveArchive, validateFingerprint, verifyArchiveBytes, type ArchiveFingerprint } from './archiveIntegrity';
import { recoverableResource } from './recoverableResource';
type Manifest = { schema: number; files: Record<string, { sha256: string; bytes: number }>; routes: Record<string, string> };
export const isEvidenceBuild = import.meta.env.MODE === 'judge';
const base = () => new URL(import.meta.env.BASE_URL, document.baseURI);
const checkedManifest = recoverableResource<Manifest>(async () => {
  return fetch(new URL('snapshots/manifest.json', base()), { signal: AbortSignal.timeout(30_000), cache: 'no-cache' }).then(async response => {
    if (!response.ok) throw new Error('The evidence manifest could not be loaded.');
    const value: Manifest = await response.json();
    if (value.schema !== 1 || !value.files || !value.routes) throw new Error('Unsupported evidence manifest.');
    return value;
  });
});

export async function projectFetch(path: string, init?: RequestInit): Promise<Response> {
  if (!isEvidenceBuild) return fetch(path, init);
  if ((init?.method ?? 'GET').toUpperCase() !== 'GET') {
    return Response.json({ detail: 'This recorded evidence build cannot start investigations.' }, { status: 403 });
  }
  const index = await checkedManifest();
  const file = index.routes[path];
  if (!file || !/^snapshots\/api\/[a-zA-Z0-9_\/-]+\.json$/.test(file) || !index.files[file]) {
    return Response.json({ detail: 'This record is not included in the evidence build.' }, { status: 404 });
  }
  const response = await fetch(new URL(file, base()), { signal: init?.signal });
  if (!response.ok) throw new Error('The recorded evidence could not be loaded.');
  const bytes = await response.arrayBuffer();
  const expected = index.files[file];
  const hash = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), byte => byte.toString(16).padStart(2, '0')).join('');
  if (bytes.byteLength !== expected.bytes || hash !== expected.sha256) throw new Error('Evidence integrity check failed. Download a fresh release.');
  return new Response(bytes, { headers: { 'Content-Type': 'application/json' } });
}

export function evidenceHref(path: string): string {
  if (!isEvidenceBuild) return path;
  if (!/^\/api\/[a-zA-Z0-9_\/-]+\/export$/.test(path)) throw new Error('Unsupported evidence download.');
  return new URL(`snapshots${path}.zip`, base()).href;
}

export function sourceBuildHref(): string {
  return new URL('downloads/counterlab-source.zip', base()).href;
}

export interface CheckedArchive {
  bytes: Uint8Array; sha256: string; expectedSource: 'release_manifest' | 'local_response_checksum';
}

export async function checkedEvidenceDownload(path: string, signal: AbortSignal,
  progress: (received: number, total: number, checking: boolean) => void): Promise<CheckedArchive> {
  if (!/^\/api\/(?:(?:research-study|evaluation|source-reproduction|source-evaluation|prediction-review)|(?:source-investigations|investigations)\/[a-f0-9]{32})\/export$/.test(path)) {
    throw new Error('This package is outside the evidence library.');
  }
  let expected: ArchiveFingerprint;
  let url: string | URL = path;
  if (isEvidenceBuild) {
    const index = await checkedManifest();
    const file = `snapshots${path}.zip`;
    expected = validateFingerprint(index.files[file] || { bytes: 0, sha256: '' });
    url = new URL(file, base());
  }
  const response = await fetch(url, { signal, redirect: 'error', cache: 'no-store' });
  if (!response.ok) throw new Error(`Package download failed (HTTP ${response.status}). No download was prepared.`);
  if (!isEvidenceBuild) {
    expected = validateFingerprint({ sha256: response.headers.get('X-CounterLab-Archive-SHA256') || '',
      bytes: Number(response.headers.get('X-CounterLab-Archive-Bytes')) });
  }
  const known = expected!;
  progress(0, known.bytes, false);
  const bytes = await receiveArchive(response, known, count => progress(count, known.bytes, false), signal);
  signal.throwIfAborted();
  progress(bytes.byteLength, known.bytes, true);
  const sha256 = await verifyArchiveBytes(bytes, known);
  signal.throwIfAborted();
  return { bytes, sha256, expectedSource: isEvidenceBuild ? 'release_manifest' : 'local_response_checksum' };
}

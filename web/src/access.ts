// The evidence build has no backend or provider connection. Never fall back to
// the live API when a snapshot is missing or fails its integrity check.
type Manifest = { schema: number; files: Record<string, { sha256: string; bytes: number }>; routes: Record<string, string> };
export const isEvidenceBuild = import.meta.env.MODE === 'judge';
const base = () => new URL(import.meta.env.BASE_URL, document.baseURI);
let manifest: Promise<Manifest> | undefined;

async function checkedManifest(): Promise<Manifest> {
  manifest ??= fetch(new URL('snapshots/manifest.json', base())).then(async response => {
    if (!response.ok) throw new Error('The evidence manifest could not be loaded.');
    const value: Manifest = await response.json();
    if (value.schema !== 1 || !value.files || !value.routes) throw new Error('Unsupported evidence manifest.');
    return value;
  });
  return manifest;
}

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

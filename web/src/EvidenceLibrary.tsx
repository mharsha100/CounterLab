import { useEffect, useRef, useState, type ReactNode } from 'react';
import { checkedEvidenceDownload, isEvidenceBuild, projectFetch } from './access';
import './library.css';

interface Package {
  id: string; title: string; kind: 'model' | 'integration' | 'analysis'; label: string;
  recommended: boolean; historical: boolean; description: string; scope: string;
  route: string; filename: string; commands: string[]; setup: string | null; expectation: string;
}
interface Check {
  state: 'fetching' | 'checking' | 'ready' | 'cancelled' | 'error'; received: number; total: number;
  error?: string; url?: string; sha256?: string; expectedSource?: string; checkedAt?: string;
}
const size = (bytes: number) => bytes < 1024 ? `${bytes} bytes` : bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
const filters = [{ value: 'all', label: 'All packages' }, { value: 'model', label: 'Real model records' },
  { value: 'integration', label: 'Simulated planning' }, { value: 'analysis', label: 'Deterministic analysis' }];

function Library() {
  const [items, setItems] = useState<Package[]>([]);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('all');
  const [checks, setChecks] = useState<Record<string, Check>>({});
  const [busy, setBusy] = useState('');
  const [receiptUrl, setReceiptUrl] = useState('');
  const controller = useRef<AbortController | null>(null);
  const urls = useRef(new Set<string>());
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    const loading = new AbortController();
    projectFetch('/api/evidence-library', { signal: loading.signal }).then(async response => {
      if (!response.ok) throw new Error('The evidence library could not be loaded.');
      const body = await response.json();
      if (mounted.current) setItems(body.items);
    }).catch(cause => { if (cause.name !== 'AbortError' && mounted.current) setError(cause.message); });
    return () => { mounted.current = false; loading.abort(); controller.current?.abort(); for (const url of urls.current) URL.revokeObjectURL(url); urls.current.clear(); };
  }, []);
  const verified = items.filter(item => checks[item.id]?.state === 'ready');
  useEffect(() => {
    const receipts = items.filter(item => checks[item.id]?.state === 'ready').map(item => ({
      package_id: item.id, filename: item.filename, route: item.route, sha256: checks[item.id].sha256,
      bytes: checks[item.id].received, checksum_source: checks[item.id].expectedSource, checked_at: checks[item.id].checkedAt,
    }));
    if (!receipts.length) { setReceiptUrl(''); return; }
    const url = URL.createObjectURL(new Blob([JSON.stringify({ schema: 1, check: 'archive_bytes_only',
      numerical_replay_in_browser: false, inference_requests: 0, files: receipts,
      limitation: 'Checks package consistency, not scientific validity, independent authorship or a trusted signature.' }, null, 2) + '\n'], { type: 'application/json' }));
    setReceiptUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [checks, items]);
  async function prepare(item: Package) {
    if (controller.current) return;
    const previous = checks[item.id]?.url;
    if (previous) { URL.revokeObjectURL(previous); urls.current.delete(previous); }
    const abort = new AbortController();
    controller.current = abort;
    setBusy(item.id);
    setChecks(current => ({ ...current, [item.id]: { state: 'fetching', received: 0, total: 0 } }));
    try {
      const archive = await checkedEvidenceDownload(item.route, abort.signal, (received, total, checking) => {
        if (mounted.current) setChecks(current => ({ ...current, [item.id]: { state: checking ? 'checking' : 'fetching', received, total } }));
      });
      if (!mounted.current || abort.signal.aborted) return;
      const url = URL.createObjectURL(new Blob([new Uint8Array(archive.bytes).buffer], { type: 'application/zip' }));
      urls.current.add(url);
      if (mounted.current) setChecks(current => ({ ...current, [item.id]: { state: 'ready', received: archive.bytes.byteLength,
        total: archive.bytes.byteLength, url, sha256: archive.sha256, expectedSource: archive.expectedSource, checkedAt: new Date().toISOString() } }));
    } catch (cause) {
      if (mounted.current) setChecks(current => ({ ...current, [item.id]: { state: abort.signal.aborted ? 'cancelled' : 'error', received: 0, total: 0,
        error: cause instanceof Error ? cause.message : 'The package could not be checked.' } }));
    } finally {
      controller.current = null;
      if (mounted.current) setBusy('');
    }
  }
  return <section className="evidence-library" aria-labelledby="library-title">
    <div className="library-intro"><div><span className="overline">TAKE THE EVIDENCE WITH YOU</span><h2 id="library-title">Choose a package. Check the bytes. Replay it.</h2><p>Eight reviewed replay packages in one place. Start with the three marked below, or filter by the kind of evidence you want to inspect.</p></div><span className="badge">No model calls to inspect or replay</span></div>
    <div className="library-disclosure"><strong>Two different checks.</strong> The browser checks ZIP size, format and SHA-256 {isEvidenceBuild ? 'against this release’s file manifest' : 'against the checksum supplied by the local server for that response'}. It does not rerun experiments. Extract a checked package and run its Python command to recompute the numerical evidence. Hashes check consistency, not authorship or scientific validity.</div>
    <div className="library-summary"><span><strong>{verified.length}</strong> of {items.length || 8} packages checked in this session</span>{receiptUrl && <a href={receiptUrl} download="counterlab-file-checks.json">Save file-check receipt ↓</a>}</div>
    <div className="library-filters" role="group" aria-label="Evidence type">{filters.map(item => <button key={item.value} disabled={!!busy} aria-pressed={filter === item.value} onClick={() => setFilter(item.value)}>{item.label}{items.length > 0 && <span>{item.value === 'all' ? items.length : items.filter(row => row.kind === item.value).length}</span>}</button>)}</div>
    {error && <p className="error-banner" role="alert">{error}</p>}
    {!items.length && !error && <p role="status">Loading the replay catalog…</p>}
    <div className="library-grid">{items.filter(item => filter === 'all' || item.kind === filter).map(item => {
      const check = checks[item.id];
      return <article className="library-card" key={item.id} aria-labelledby={`package-${item.id}`}>
        <div className="library-card-top"><span className={`library-kind library-kind-${item.kind}`}>{item.label}</span><span>{item.recommended ? 'START HERE' : item.historical ? 'HISTORICAL' : 'SUPPORTING'}</span></div>
        <h3 id={`package-${item.id}`}>{item.title}</h3><p>{item.description}</p>
        {item.setup && <div className="library-setup"><strong>Reference setup required</strong><p>{item.setup}</p></div>}
        <div className="library-actions">{check?.state === 'ready' ? <a className="button button-primary" href={check.url} download={item.filename}>Save checked ZIP ↓</a> : <button className="button button-primary" disabled={!!busy} onClick={() => prepare(item)} aria-label={`Check package: ${item.title}`}>{busy === item.id ? 'Checking package…' : 'Check package →'}</button>}{busy === item.id && <button className="button button-secondary" onClick={() => controller.current?.abort()}>Cancel</button>}{check?.state === 'ready' && <span className="library-checked">✓ File integrity checked · {size(check.received)}</span>}</div>
        {(check?.state === 'fetching' || check?.state === 'checking') && <div className="library-progress" role="status"><progress max={check.total || 1} value={check.received} aria-label={`Download progress: ${item.title}`} /><p>{check.state === 'checking' ? 'Checking SHA-256…' : check.total ? `Received ${size(check.received)} of ${size(check.total)}` : 'The server is verifying and preparing this package…'}</p></div>}
        {check?.state === 'error' && <p className="library-failure" role="alert">{check.error}</p>}
        {check?.state === 'cancelled' && <p className="library-caption" role="status">Check cancelled. No file was prepared.</p>}
        {check?.state === 'ready' && <details className="library-fingerprint"><summary>Inspect the file fingerprint</summary><code>{check.sha256}</code><p>{check.expectedSource === 'release_manifest' ? 'Matched the portable release manifest.' : 'Matched the checksum for this local server response.'} Numerical replay has not run in the browser.</p><button className="text-button" disabled={!!busy} onClick={() => prepare(item)}>Check a fresh response</button></details>}
        <details className="library-replay"><summary>How to replay and what it verifies</summary><ol><li>Save the checked ZIP and extract it into a new folder.</li><li>Open a terminal in that folder. Use Python 3.13; no extra packages, API key or Docker are needed.</li>{item.setup && <li>Complete the explicit reference setup described above.</li>}<li>Run {item.commands.map(command => <code key={command}>{command}</code>)}</li></ol><p>{item.expectation}</p><p>Saved model replies are not regenerated. Stop if the replay reports a failed check; retain that result for inspection.</p></details>
        <p className="library-scope"><strong>Scope:</strong> {item.scope}</p>
      </article>;
    })}</div>
  </section>;
}

export default function EvidenceWorkspace({ children }: { children: ReactNode }) {
  const [view, setView] = useState('library');
  return <div className="evidence-workspace"><div className="study-tabs library-tabs" role="group" aria-label="Evidence views"><button aria-pressed={view === 'library'} onClick={() => setView('library')}>Evidence library</button><button aria-pressed={view === 'record'} onClick={() => setView('record')}>Selected investigation</button></div>{view === 'library' ? <Library /> : children}</div>;
}

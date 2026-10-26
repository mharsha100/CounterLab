import { useEffect, useState } from 'react';
import { isEvidenceBuild, projectFetch } from './access';
import './trace.css';

interface Frame {
  step: number; page: number; hit: boolean; evicted: number | null; decision: string;
  cache_before: number[]; cache_after: number[]; history_before: number; history_after: number;
  unrevealed_before: number; gate_checked: boolean; gate_threshold: number | null;
  gate_earned: boolean; budget_before: number; budget_after: number; misses_so_far: number; credits_so_far: number;
}
interface Profile { history_refresh: string; misses: number; gate_credits: number; events_sha256: string; frames: Frame[] }
interface TraceCase {
  case_id: string; label: string; capacity: number; requests: number[]; profiles: Profile[];
  milestones: { history: number | null; decision: number | null; hit_miss: number | null };
  saved_evidence_id: string | null;
}
interface Trace { cases: TraceCase[]; seed: number; tau: number; protocol_sha256: string; limits: string[] }
const decisions: Record<string, string> = {
  hit: 'Already in memory', warmup: 'Fill an empty slot', l0_prediction: 'Evict using a forecast',
  support_prediction: 'Use a prediction credit', support_priority: 'Use the fixed random priority',
};

function explain(step: number, left?: Frame, right?: Frame): string {
  if (!step || !left || !right) return 'Both caches start empty. A page is a numbered item; the cache is the limited memory that holds it. Move forward to serve the first request.';
  if (left.hit !== right.hit) return `Page ${left.page} is already in one cache and absent from the other. Earlier eviction choices now change the running miss counts.`;
  if (left.gate_earned !== right.gate_earned) return 'The saved history values produce different gate checks. Only one rule earns a prediction credit, changing how it chooses a page to evict. A credit is permission to use a forecast, not money or an API token.';
  if (left.evicted !== right.evicted) return 'Both rules miss, but choose different pages to evict. Compare the memory tiles to see what each rule keeps for the next request.';
  if (left.hit && right.hit && left.history_after !== right.history_after) return 'Both rules hit: no page needs loading. The miss-only rule keeps its saved history; the every-request rule refreshes it. A difference in state can appear before a difference in cost.';
  if (left.decision === 'warmup' && right.decision === 'warmup') return `Page ${left.page} is absent from both caches. Each fills an empty slot and counts one miss. These warmup misses are included in the totals here.`;
  if (left.hit && right.hit) return `Page ${left.page} is already in both caches. Both serve a hit, so neither miss count increases.`;
  return 'Both caches miss on this request and apply the same eviction decision. Equal results here do not establish that the two rules agree on every input.';
}

function Memory({ profile, frame, other, capacity, step }: { profile: Profile; frame?: Frame; other?: Frame; capacity: number; step: number }) {
  const cache = frame?.cache_after || [];
  return <article className="trace-memory">
    <div className="trace-memory-title"><h4>{profile.history_refresh === 'after_miss' ? 'Update after a miss' : 'Update after every request'}</h4><span>{step === 0 ? 'Empty' : frame?.hit ? 'Hit' : 'Miss'}</span></div>
    <p className="trace-action">{step === 0 ? 'Waiting for the first request' : `${decisions[frame!.decision] || frame!.decision}${frame!.evicted === null ? '' : ` · evicted page ${frame!.evicted}`}`}</p>
    <ol className="trace-cache" aria-label={`${profile.history_refresh === 'after_miss' ? 'Miss-only' : 'Every-request'} cache after ${step} requests`}>
      {Array.from({ length: capacity }, (_, index) => {
        const page = cache[index];
        const requested = page !== undefined && page === frame?.page;
        const different = page !== undefined && !other?.cache_after.includes(page);
        return <li key={index} className={`${requested ? 'trace-requested' : ''} ${different ? 'trace-different' : ''}`} aria-label={page === undefined ? 'Empty slot' : `Page ${page}${requested ? ', requested now' : ''}${different ? ', absent from the other cache' : ''}`}>{page ?? '–'}</li>;
      })}
    </ol>
    <dl className="trace-metrics"><div><dt>Misses so far</dt><dd>{frame?.misses_so_far ?? 0}</dd></div><div><dt>Credits earned</dt><dd>{frame?.credits_so_far ?? 0}</dd></div><div><dt>History Y · before → after</dt><dd className={`trace-history ${frame?.history_before !== other?.history_before || frame?.history_after !== other?.history_after ? 'trace-value-different' : ''}`}>{frame ? `${frame.history_before} → ${frame.history_after}` : '0 → 0'}</dd></div></dl>
    {frame && <details className="trace-calculation"><summary>Inspect this decision</summary><p>Memory before: {frame.cache_before.length ? frame.cache_before.join(', ') : 'empty'}.</p><p>Saved history: {frame.history_before} → {frame.history_after}. Credit budget: {frame.budget_before} → {frame.budget_after}.</p>{frame.gate_checked ? <p>Gate check: U = {frame.unrevealed_before} ≤ (Y + 2) / e − 2 = {frame.gate_threshold!.toFixed(3)}. <strong>{frame.gate_earned ? 'Passed: one credit earned.' : 'Not passed: no credit earned.'}</strong> Threshold shown rounded; the runner compares full precision.</p> : <p>No gate check on this request. It is a hit, fills an empty slot, or uses the separate outside-support rule.</p>}</details>}
  </article>;
}

export default function TraceExplorer() {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<Trace | null>(null);
  const [error, setError] = useState('');
  const [caseIndex, setCaseIndex] = useState(0);
  const [step, setStep] = useState(0);
  const [download, setDownload] = useState('');
  useEffect(() => {
    if (!open || data) return;
    const controller = new AbortController();
    setError('');
    projectFetch('/api/trace-explorer', { signal: controller.signal }).then(async response => {
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || 'The trace could not be verified.');
      setData(body);
    }).catch(cause => { if (cause.name !== 'AbortError') setError(cause.message); });
    return () => controller.abort();
  }, [open, data]);
  useEffect(() => {
    if (!data) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2) + '\n'], { type: 'application/json' }));
    setDownload(url);
    return () => URL.revokeObjectURL(url);
  }, [data]);
  const selected = data?.cases[caseIndex];
  const left = selected?.profiles[0].frames[step - 1];
  const right = selected?.profiles[1].frames[step - 1];
  return <section className="trace-explorer" aria-labelledby="trace-title">
    <div className="trace-heading"><div><span className="overline">UNDERSTAND THE MECHANISM</span><h3 id="trace-title">What actually changes inside the cache?</h3><p>Step through a short, constructed example and two controls. This is separate from the recorded source task above.</p></div><button className="button button-secondary" aria-expanded={open} aria-controls="trace-panel" onClick={() => setOpen(!open)}>{open ? 'Close trace explorer ↑' : 'Open trace explorer →'}</button></div>
    {open && <div id="trace-panel">
      {error && <p role="alert" className="error-banner">{error}</p>}
      {!data && !error && <p role="status">{isEvidenceBuild ? 'Checking the packaged trace…' : 'Replaying the fixed diagnostic trace…'}</p>}
      {data && selected && <>
        <div className="trace-toolbar"><div><label htmlFor="trace-case">Choose a reviewed example</label><select id="trace-case" value={caseIndex} onChange={event => { setCaseIndex(Number(event.target.value)); setStep(0); }}>{data.cases.map((item, index) => <option key={item.case_id} value={index}>{item.label}</option>)}</select></div><span>{selected.capacity} slots · {selected.requests.length} requests · seed {data.seed} · τ {data.tau}</span></div>
        <div className="trace-legend"><span>● Requested page</span><span>◇ Absent from the other cache</span><span>Tiles show sorted page IDs, not slot order.</span></div>
        <div className="trace-request"><div><span className="overline">{step ? `REQUEST ${step} OF ${selected.requests.length}` : 'BEFORE ANY REQUEST'}</span><strong>{step ? `Request page ${selected.requests[step - 1]}` : 'Both rules get the same input.'}</strong></div><span className="badge">No model calls</span></div>
        <label className="trace-slider-label" htmlFor="trace-step">Requests served: {step} of {selected.requests.length}</label><input id="trace-step" type="range" min={0} max={selected.requests.length} value={step} onChange={event => setStep(Number(event.target.value))} aria-valuetext={step ? `Request ${step}, page ${selected.requests[step - 1]}` : 'Before any request'} />
        <div className="trace-transport"><button className="button button-secondary" disabled={step === 0} onClick={() => setStep(step - 1)}>← Back one</button><button className="text-button" onClick={() => setStep(0)}>Reset to start</button><button className="button button-primary" disabled={step === selected.requests.length} onClick={() => setStep(step + 1)}>Next request →</button></div>
        <div className="trace-jumps" aria-label="Jump to a difference">{([['history', 'History first differs'], ['decision', 'Decision first differs'], ['hit_miss', 'Hit / miss first differs']] as const).map(([key, label]) => <button key={key} className="button button-secondary" disabled={selected.milestones[key] === null} onClick={() => setStep(selected.milestones[key]!)} aria-label={`Jump to: ${label}`}>{label} <strong>{selected.milestones[key] === null ? 'none' : `#${selected.milestones[key]}`}</strong></button>)}</div>
        <p className="trace-explanation" aria-live="polite" aria-atomic="true">{explain(step, left, right)}</p>
        <div className="trace-pair"><Memory profile={selected.profiles[0]} frame={left} other={right} step={step} capacity={selected.capacity} /><Memory profile={selected.profiles[1]} frame={right} other={left} step={step} capacity={selected.capacity} /></div>
        <p className="trace-scope">Counts include the initial warmup. {isEvidenceBuild ? 'States were recomputed when this package was built; moving the slider inspects saved states.' : 'States are recomputed by the local Python runner; moving the slider inspects those states.'} Neither action calls a model or Docker.</p>
        <details className="trace-calculation"><summary>Definitions, verification and limits</summary><dl className="trace-glossary"><div><dt>Hit / miss</dt><dd>A hit finds the page in memory. A miss loads it, evicting a resident page if memory is full.</dd></div><div><dt>History (Y) / current state (U)</dt><dd>U counts the algorithm’s unrevealed layers. Y saves a previous U value. The two rules change only when Y is refreshed; U is not a miss count.</dd></div><div><dt>Gate / credit</dt><dd>The gate is a numerical condition checked on a support miss. Passing earns permission for a forecast-based eviction. The budget can also be reset by a separate rule.</dd></div></dl><p>Protocol SHA-256</p><code>{data.protocol_sha256}</code>{selected.saved_evidence_id && <><p>Original witness evidence ID</p><code>{selected.saved_evidence_id}</code></>}<p>Event fingerprints: after-miss / every-request</p>{selected.profiles.map(profile => <code key={profile.history_refresh}>{profile.events_sha256}</code>)}<ul>{data.limits.map(limit => <li key={limit}>{limit}</li>)}</ul><p>Reproduce locally from the source build: <code>python scripts/inspect_trace.py</code></p><a className="button button-secondary" href={download} download="counterlab-diagnostic-traces.json">Download all three traces ↓</a></details>
      </>}
    </div>}
  </section>;
}

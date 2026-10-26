import { projectFetch, evidenceHref, isEvidenceBuild, sourceBuildHref } from './access';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import ResearchStudy from './ResearchWorkspace';
import Evaluation from './EvaluationWorkspace';
import VerifiedFinding from './VerifiedFinding';
import Demonstration from './Demonstration';
import EvidenceWorkspace from './EvidenceLibrary';
import ClaimAudit from './ClaimAudit';
import type { Attempt, Investigation, RunItem, Source, Workspace } from './types';

type View = 'investigation' | 'sources' | 'evidence' | 'history' | 'research' | 'evaluation' | 'demo';
type IconName = 'arrow' | 'activity' | 'book' | 'file' | 'history' | 'check' | 'close' | 'download' | 'external' | 'play' | 'chevron';
const paths: Record<IconName, string> = {
  arrow: 'M5 12h14m-5-5 5 5-5 5', activity: 'M3 12h4l3-8 4 16 3-8h4',
  book: 'M3 5c4-2 6-1 9 1 3-2 5-3 9-1v15c-4-2-6-1-9 1-3-2-5-3-9-1V5Zm9 1v15',
  file: 'M14 3H5v18h14V8l-5-5Zm0 0v5h5M8 12h8m-8 4h6',
  history: 'M3 10a9 9 0 1 1 1 7M3 4v6h6m3-3v6l4 2',
  check: 'm5 12 4 4L19 6', close: 'm6 6 12 12M6 18 18 6',
  download: 'M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5',
  external: 'M14 3h7v7m0-7L10 14M10 4H4v16h16v-6',
  play: 'm9 5 10 7-10 7V5Z', chevron: 'm9 5 7 7-7 7',
};
function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>;
}
function Brand() {
  return <div className="brand"><span className="brand-mark"><svg width="26" height="26" viewBox="0 0 40 40" fill="none" aria-hidden="true"><path d="M8 14h23l-6-6M32 26H9l6 6" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" /></svg></span><span>CounterLab<span className="brand-dot">.</span></span></div>;
}
class ApiError extends Error { constructor(message: string, public status: number) { super(message); } }
async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await projectFetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new ApiError(typeof data.detail === 'string' ? data.detail : 'The request could not be completed.', response.status);
  return data as T;
}
const date = (value: string) => new Date(value).toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' });
const number = (value: number | undefined) => value === undefined ? '—' : value.toLocaleString('en-US');
const active = (state: string) => state === 'running' || state === 'queued';
const sourceName: Record<string, string> = {
  support_protocol: 'Supporting reproduction · protocol', support_implementation: 'Supporting reproduction · implementation',
  challenge_implementation_excerpt: 'Challenging reproduction · code excerpt', official_implementation: 'Original implementation · reference',
};

function Modal({ open, close, children, label, drawer = false }: { open: boolean; close: () => void; children: ReactNode; label: string; drawer?: boolean }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => { if (open && !ref.current?.open) ref.current?.showModal(); else if (!open && ref.current?.open) ref.current.close(); }, [open]);
  return <dialog ref={ref} className={drawer ? 'drawer' : 'modal'} aria-label={label} onCancel={close}
    onClick={event => { if (event.target === ref.current) { const bounds = ref.current.getBoundingClientRect(); if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) close(); } }}>
    <button className="icon-button modal-close" aria-label="Close dialog" onClick={close}><Icon name="close" /></button>{children}
  </dialog>;
}

function Measurement({ attempt }: { attempt: Attempt }) {
  const evidence = attempt.evidence!;
  return <div className="measurement"><div className="mini-heading"><span>MEASURED RESULT</span><span className="verified"><Icon name="check" size={13} /> Replay verified</span></div>
    <table><thead><tr><th>History refreshed</th><th>Gate credits</th><th>Cache misses</th></tr></thead>
      <tbody>{evidence.profiles.map((profile, i) => <tr key={profile.history_refresh}><td><span className={`variant-dot dot-${i}`} />{i === 0 ? 'After a miss' : 'After every request'}</td><td>{profile.gate_credits}</td><td><strong>{profile.misses}</strong><span className="bar-track"><span style={{ width: `${100 * profile.misses / attempt.request_count}%` }} className={`bar bar-${i}`} /></span></td></tr>)}</tbody></table>
    <p className="table-note">One credit permits one prediction-based eviction. Misses count requests absent from the cache.</p>
  </div>;
}

function AttemptCard({ attempt }: { attempt: Attempt }) {
  const rejected = attempt.state === 'rejected';
  const profiles = attempt.evidence?.profiles;
  const differs = profiles && (profiles[0].misses !== profiles[1].misses || profiles[0].gate_credits !== profiles[1].gate_credits);
  return <article className={`attempt-card ${rejected ? 'rejected-card' : ''}`}>
    <div className="attempt-top"><span className="overline">PROPOSAL {String(attempt.number).padStart(2, '0')} <span className="muted">/ {attempt.plan.case_id.replace('_', ' ').toUpperCase()}</span></span>
      <span className={`badge ${rejected ? 'badge-amber' : attempt.evidence ? 'badge-green' : ''}`}><span className="status-dot" />{rejected ? 'Rejected before execution' : attempt.evidence ? 'Experiment measured' : 'Checking proposal'}</span></div>
    <h3>{rejected ? 'This test cannot separate the rules.' : attempt.evidence ? differs ? (attempt.number > 1 ? 'The follow-up reveals a difference.' : 'This test reveals a difference.') : 'The measured outcomes agree.' : 'Test the history rule.'}</h3>
    <div className="input-chips"><span>{attempt.capacity} cache slots</span><span>{attempt.request_count} requests</span><span>Same inputs & seed</span></div>
    <details className="hypothesis"><summary>Read the model’s proposed explanation <span>Unverified proposal</span></summary><p>{attempt.plan.hypothesis}</p></details>
    <div className="predictions"><span className="small-label">PRECOMMITTED PREDICTIONS</span><div><span>Gate behavior: <strong>{attempt.plan.predict_gate_difference ? 'different' : 'same'}</strong></span><span>Miss counts: <strong>{attempt.plan.predict_miss_difference ? 'different' : 'same'}</strong></span></div></div>
    {rejected && <div className="rejection-reason"><span className="reason-symbol">!</span><div><strong>The mathematical check found a contradiction</strong><p>{attempt.preflight?.reasons[0]?.reason === 'all_distinct_pages_fit' ? 'Every requested page fits in the cache. There are no later evictions for the history rule to change.' : `With ${attempt.capacity} cache slots, the gate cannot activate under either rule. This plan’s prediction of a difference is impossible.`}</p><details><summary>Show the check</summary>{attempt.preflight?.reasons.map(reason => <p key={reason.reason}>{reason.explanation}</p>)}</details></div></div>}
    {attempt.evidence && <><Measurement attempt={attempt} /><div className={`prediction-result ${attempt.predictions_correct ? '' : 'prediction-mismatch'}`}><Icon name={attempt.predictions_correct ? 'check' : 'activity'} size={15} />{attempt.predictions_correct ? 'Both predictions matched the measurements.' : 'The measurements differed from the model’s predictions.'}</div></>}
  </article>;
}

function Sources({ sources }: { sources: Source[] }) {
  return <section className="sources-view"><div className="section-title"><div><span className="overline">SOURCE TRAIL</span><h2>Where the comparison begins.</h2></div><span className="badge">4 pinned sources</span></div>
    <p className="section-intro">Our source inspection identified differences in implementation contracts. The experiment changes one rule in our independently written reference. It does not reproduce either full report.</p>
    {sources.map(source => <article className="source-card" key={source.id}><div className="source-title"><span className="source-icon"><Icon name="book" /></span><div><h3>{sourceName[source.id]}</h3><p>{source.role}</p></div><a className="icon-button" href={source.url} target="_blank" rel="noreferrer" aria-label={`Open ${sourceName[source.id]}`}><Icon name="external" /></a></div>
      <dl className="contract-grid">{Object.entries(source.observed_contract).map(([key, value]) => <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd>{Array.isArray(value) ? value.join(', ') : String(value)}</dd></div>)}</dl><div className="source-hash"><span>SHA-256</span><code>{source.sha256}</code></div></article>)}
    <div className="scope-note"><Icon name="file" /><p>External implementations were inspected as text. Their source code is not executed or redistributed by this app.</p></div>
  </section>;
}

function SourceWorkspace({ sources }: { sources: Source[] }) {
  const [audit, setAudit] = useState(true);
  return <><div className="study-tabs research-switch" role="group" aria-label="Source views"><button aria-pressed={audit} onClick={() => setAudit(true)}>Claim audit</button><button aria-pressed={!audit} onClick={() => setAudit(false)}>Original source cards</button></div>{audit ? <ClaimAudit /> : <Sources sources={sources} />}</>;
}

export default function App() {
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [runs, setRuns] = useState<RunItem[]>([]);
  const [selected, setSelected] = useState('');
  const [record, setRecord] = useState<Investigation | null>(null);
  const [view, setView] = useState<View>(() => {
    const requested = new URLSearchParams(window.location.search).get('view');
    const aliases: Record<string, View> = { 'source-investigator': 'research', 'source-reproduction': 'research', 'controlled-study': 'research', 'source-evaluation': 'evaluation', 'experiment-workbench': 'research', 'claim-audit': 'sources', demo: 'demo', investigation: 'investigation',
      sources: 'sources', research: 'research', evaluation: 'evaluation', evidence: 'evidence', history: 'history' };
    return Object.hasOwn(aliases, requested || '') ? aliases[requested!] : 'demo';
  });
  const [freshEvaluation, setFreshEvaluation] = useState(() => new URLSearchParams(window.location.search).get('view') === 'source-evaluation');
  const [error, setError] = useState('');
  const [launch, setLaunch] = useState(false);
  const [drawer, setDrawer] = useState(false);
  const [consent, setConsent] = useState(false);
  const [cap, setCap] = useState(8192);
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState('');
  const [search, setSearch] = useState('');
  const historySearch = useRef<HTMLInputElement>(null);
  const requestId = useRef('');

  useEffect(() => {
    Promise.all([api<Workspace>('/api/workspace'), api<{ items: RunItem[] }>('/api/investigations')])
      .then(([meta, listing]) => { setWorkspace(meta); setRuns(listing.items.filter(row => row.adapter !== 'source')); setSelected(meta.recorded_run_id); })
      .catch(cause => setError(cause.message));
  }, []);

  useEffect(() => {
    if (!selected) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    setRecord(null);
    async function refresh() {
      try {
        const next = await api<Investigation>(`/api/investigations/${selected}`);
        if (cancelled) return;
        setRecord(next); setError('');
        const listing = await api<{ items: RunItem[] }>('/api/investigations');
        if (!cancelled) setRuns(listing.items.filter(row => row.adapter !== 'source'));
        if (active(next.state) && !cancelled) timer = setTimeout(refresh, 1000);
      } catch (cause) {
        if (cancelled) return;
        if (cause instanceof ApiError && cause.status === 503) timer = setTimeout(refresh, 700);
        else setError(cause instanceof Error ? cause.message : 'The record could not be loaded.');
      }
    }
    refresh();
    return () => { cancelled = true; clearTimeout(timer); };
  }, [selected]);

  function openLaunch() {
    requestId.current = crypto.randomUUID().replaceAll('-', '');
    setConsent(false); setStartError(''); setLaunch(true);
  }
  async function start() {
    if (!consent || starting) return;
    setStarting(true); setStartError('');
    try {
      const result = await api<{ id: string }>('/api/investigations', {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CounterLab-Action': 'start-investigation' },
        body: JSON.stringify({ confirm_credit_use: true, request_id: requestId.current, max_output_tokens: cap }),
      });
      setSelected(result.id); setView('investigation'); setLaunch(false);
    } catch (cause) { setStartError(cause instanceof Error ? cause.message : 'Could not start the investigation.'); }
    finally { setStarting(false); }
  }
  const measured = record?.attempts.filter(attempt => attempt.evidence).at(-1);
  const working = runs.some(run => active(run.state));
  const filteredRuns = runs.filter(run => `${run.id} ${run.state} ${run.kind}`.includes(search.trim().toLowerCase()));
  const nav: { id: View; label: string; icon: IconName }[] = [
    { id: 'demo', label: 'Guided demonstration', icon: 'play' },
    { id: 'investigation', label: 'Investigation', icon: 'activity' }, { id: 'sources', label: 'Sources', icon: 'book' },
    { id: 'research', label: 'Research study', icon: 'check' }, { id: 'evaluation', label: 'Evaluation', icon: 'activity' }, { id: 'evidence', label: 'Evidence', icon: 'file' }, { id: 'history', label: 'Run history', icon: 'history' },
  ];

  return <div className="app-shell">
    <aside className="sidebar"><Brand /><div className="workspace-label"><span className="status-dot" /> {isEvidenceBuild ? 'RECORDED EVIDENCE' : 'LOCAL RESEARCH WORKSPACE'}</div>
      <div className="sidebar-section"><span className="sidebar-eyebrow">YOUR INVESTIGATION</span><div className="case-switch"><span className="case-index">01</span><div><strong>Learning-augmented paging</strong><span>History timing</span></div></div></div>
      <nav aria-label="Workspace">{nav.map(item => <button key={item.id} className={`nav-item ${view === item.id ? 'selected' : ''}`} aria-current={view === item.id ? 'page' : undefined} onClick={() => setView(item.id)}><Icon name={item.icon} />{item.label}</button>)}</nav>
      <div className="sidebar-note"><span className="small-label">ONE FACTOR AT A TIME</span><p>A useful experiment separates explanations. Every attempt stays in the record.</p><span className="note-line" /></div>
      <div className="sidebar-footer"><span className="local-dot" /><div><strong>{isEvidenceBuild ? 'Evidence edition' : 'Local development'}</strong><span>Reviewed adapters only</span></div><span className="version">v0.1</span></div>
    </aside>
    <div className="main-shell"><header className="topbar"><div className="breadcrumbs">Workspace <Icon name="chevron" size={12} /><strong>Paging</strong></div><div className="sponsors"><span>Powered by</span><strong>NEBIUS</strong><span className="sponsor-divider" /><strong className="nvidia-word"><span className="nvidia-square" /> NVIDIA <span>Nemotron</span></strong></div></header>
      <main><div className="page-heading"><div><div className="heading-eyebrow"><span className="tiny-square" /> COMPUTATIONAL RESEARCH <span>/</span> CASE 01</div><h1>{view === 'demo' ? 'Follow the evidence.' : view === 'evaluation' ? 'Measure the investigator, too.' : view === 'research' ? 'Test the conditions behind the claim.' : view === 'sources' ? 'Follow the source trail.' : view === 'evidence' ? 'Evidence you can inspect.' : view === 'history' ? 'Every attempt, preserved.' : 'Turn disagreement into experiments.'}</h1><p>{view === 'demo' ? 'A recorded experiment, a failed prediction and the complete comparison.' : view === 'evaluation' ? 'A frozen comparison of experiment selection, evidence accuracy and honest abstention.' : view === 'research' ? 'Inspect source contracts, controlled settings, null results and a replayable finite study.' : view === 'sources' ? 'Trace each question to its contract, measured evidence and remaining gaps.' : view === 'evidence' ? 'Find the reviewed replay packages, check their bytes and reproduce the results locally.' : 'Investigate when a change in an algorithm’s history rule changes its behavior.'}</p></div>
        {view !== 'demo' && view !== 'evidence' && !isEvidenceBuild && !workspace?.read_only && <button className="button button-primary new-run" onClick={openLaunch} disabled={!workspace?.live_configured || working || !record}><Icon name="play" size={16} /> New investigation</button>}</div>
      {error && <div className="error-banner" role="alert"><strong>Could not load the workspace.</strong> {error}<button className="text-button" onClick={() => window.location.reload()}>Try again</button></div>}
      {isEvidenceBuild && <div className="notice evidence-notice"><strong>Recorded evidence build.</strong> Results were verified when packaged. No new model call or numerical replay runs in this browser. Download a replay to verify locally; the full source build contains the live workflow. <a href={sourceBuildHref()}>Download source &amp; live workflow ↓</a></div>}
      {workspace?.read_only && !isEvidenceBuild && <div className="notice">Read-only demonstration. Investigation starts are blocked by the server; API credentials are not loaded.</div>}
      {!workspace?.live_configured && workspace && !workspace.read_only && <div className="notice">Recorded evidence is available. Live investigations need the local Nebius configuration and the experiment worker running in Docker Desktop.</div>}
      {!['research', 'evaluation', 'demo', 'evidence', 'sources'].includes(view) && <div className="record-strip"><div><span className={`badge ${record?.kind === 'recorded' ? 'badge-neutral' : 'badge-green'}`}><span className="status-dot" />{record?.provider_mode === 'simulated_provider' ? 'Offline verification · simulated model' : record?.kind === 'recorded' ? 'Recorded run' : record && active(record.state) ? 'Live investigation' : record ? 'Saved live run' : 'Loading record'}</span><span className="record-time">{record ? date(record.created_at) : 'Opening verified evidence…'}</span></div><span className="development-label">Development case <span title="Previously explored, constructed inputs. Full paper reproduction remains open.">i</span></span></div>}
      {view === 'demo' ? <Demonstration onEvaluation={() => { setFreshEvaluation(true); setView('evaluation'); }} /> : view === 'evaluation' ? <Evaluation initialFresh={freshEvaluation} /> : view === 'research' ? <ResearchStudy /> : view === 'sources' && workspace ? <SourceWorkspace sources={workspace.sources.sources} /> : view === 'history' ? <section className="history-view"><div className="section-title"><h2>Investigation history</h2><input ref={historySearch} type="search" aria-label="Filter investigations" placeholder="Filter by run ID or status" value={search} onChange={event => setSearch(event.target.value)} /></div>
        <div className="history-list">{filteredRuns.map(run => <button key={run.id} className="history-row" onClick={() => { setSelected(run.id); setView('investigation'); }}><span className="history-icon"><Icon name={run.kind === 'recorded' ? 'history' : 'activity'} /></span><div><strong>{run.provider_mode === 'simulated_provider' ? 'Offline verification · simulated model' : run.kind === 'recorded' ? 'Verified recorded investigation' : active(run.state) ? 'Live investigation' : 'Saved investigation'}</strong><span>{date(run.created_at)} · {run.id.slice(0, 8)}</span></div><span className={`badge ${run.state === 'completed' ? 'badge-green' : ''}`}>{run.state.replaceAll('_', ' ')}</span><Icon name="arrow" /></button>)}</div>{workspace && filteredRuns.length === 0 && <div className="empty-card history-empty" role="status"><p>{search.trim() ? 'No investigations match this filter.' : 'No saved investigations are available.'}</p>{search.trim() && <button className="button button-secondary" onClick={() => { setSearch(''); historySearch.current?.focus(); }}>Clear filter</button>}</div>}</section> : view === 'evidence' ? <EvidenceWorkspace>{record ? <section className="evidence-view"><div className="section-title"><div><span className="overline">REPRODUCIBLE BY DESIGN</span><h2>Measurements from the reviewed runner.</h2></div><button className="button button-secondary" onClick={() => setDrawer(true)}><Icon name="file" /> Inspect record</button></div>
        <p className="section-intro">{isEvidenceBuild ? 'Measurements below were recomputed from the frozen inputs when this release was packaged.' : 'Measurements below are recomputed from the committed inputs before the API displays them.'} The factual report cites every measured test; model hypotheses remain separate.</p>{measured ? <Measurement attempt={measured} /> : <div className="empty-card">No experimental measurements have been recorded in this run.</div>}<div className="verification-grid">{[['Protocol hash', record.provenance.protocol_verified], ['Record manifest', record.provenance.manifest_verified], ['Numerical replay', record.provenance.numerical_replay_verified]].map(([label, checked]) => <div key={String(label)}><span className={checked ? 'verified-icon' : 'pending-icon'}><Icon name={checked ? 'check' : 'activity'} /></span><strong>{label}</strong><span>{checked ? 'Verified' : 'Pending'}</span></div>)}</div><div className="hash-panel"><span className="small-label">COMMITTED PROTOCOL · SHA-256</span><code>{record.protocol.sha256}</code></div>
        {record.export_available && <div className="export-panel"><div><h3>Take the evidence with you.</h3><p>Includes committed plans, measured results, hashes, and a Python replay. Replaying uses no credits.</p></div><a className="button button-primary" href={evidenceHref(`/api/investigations/${record.id}/export`)}><Icon name="download" /> Download evidence</a></div>}</section> : <p role="status">Opening the selected investigation…</p>}</EvidenceWorkspace> : <>
      <div className="comparison"><article><div className="variant-label"><span className="variant-dot dot-0" /> VARIANT A</div><h2>Update after a miss.</h2><p>Keep the history value unchanged when the requested page is already in the cache.</p><span className="rule-label">History refresh: after_miss</span></article><div className="comparison-connector"><span>vs</span></div><article><div className="variant-label"><span className="variant-dot dot-1" /> VARIANT B</div><h2>Update after every request.</h2><p>Refresh the history value after every request, including a cache hit.</p><span className="rule-label">History refresh: after_request</span></article></div>
      <p className="comparison-caption">Our controlled variants, informed by source inspection. <button className="text-button" onClick={() => setView('sources')}>Inspect the sources <Icon name="external" size={11} /></button></p>
      <div className="investigation-grid"><section className="timeline-section"><div className="section-title"><h2>The investigation</h2><span>{record?.attempts.length || 0} proposals <span className="muted">/</span> {record?.attempts.filter(attempt => attempt.evidence).length || 0} measured</span></div>
        {!record && !error && <div className="loading-card"><span className="spinner" /> Opening the evidence record…</div>}
        {record?.attempts.map((attempt, index) => <div key={attempt.number} id={`attempt-${attempt.number}`} className="timeline-step"><span className={`timeline-node ${attempt.state === 'rejected' ? 'node-amber' : 'node-green'}`}>{attempt.state === 'rejected' ? '!' : <Icon name="check" size={13} />}</span><AttemptCard attempt={attempt} />{index < record.attempts.length - 1 && <div className="followup-caption"><Icon name="arrow" size={14} /> Nemotron revises the experiment after feedback</div>}</div>)}
        {record && active(record.state) && <div className="live-progress" role="status"><span className="spinner" /><div><strong>{record.phase}</strong><p>Showing saved progress. Up to {record.protocol.maximum_inference_requests} model requests; no automatic retries.</p></div></div>}
        {record?.error && <div className="error-banner" role="alert"><strong>{record.phase}.</strong> {record.error.replaceAll('_', ' ')}. The attempt is preserved. Check the local configuration or connection before starting another run.</div>}
        {record?.review_reason && <div className="notice">Review needed: {record.review_reason.replaceAll('_', ' ')}. This run is preserved; it has not been retried.</div>}
        {record && !active(record.state) && <VerifiedFinding record={record} />}
      </section><aside className="inspector"><div className="protocol-card"><div className="section-title"><h3>The reviewed protocol</h3><Icon name="file" size={17} /></div><div className="protocol-change"><span className="small-label">ONE CHANGED FACTOR</span><strong>History-update timing</strong></div><dl className="protocol-facts"><div><dt>Inputs</dt><dd>3 reviewed cases</dd></div><div><dt>Random seed</dt><dd>{record?.protocol.seed ?? 0}</dd></div><div><dt>Initial budget (τ)</dt><dd>{record?.protocol.tau ?? 0}</dd></div><div><dt>Cache at start</dt><dd>Empty</dd></div><div><dt>Everything else</dt><dd>Held fixed</dd></div></dl><details><summary>What stays fixed?</summary><ul>{record?.protocol.held_fixed.map(factor => <li key={factor}>{factor}</li>)}</ul></details><button className="button button-secondary full-width" onClick={() => setDrawer(true)} disabled={!record}>Inspect protocol <Icon name="arrow" size={15} /></button></div>
        <div className="run-card"><span className="small-label">THIS RUN</span><dl className="protocol-facts"><div><dt>Model</dt><dd>Nemotron 3 Ultra</dd></div><div><dt>Provider</dt><dd>{record?.provider_mode === 'simulated_provider' ? 'Simulated provider' : 'Nebius Token Factory'}</dd></div><div><dt>Model requests</dt><dd>{record && active(record.state) ? 'In progress' : `${record?.inference_requests ?? '—'} / ${record?.protocol.maximum_inference_requests ?? '—'}`}</dd></div><div><dt>Reported tokens</dt><dd>{number(record?.usage.total_tokens)}</dd></div><div><dt>Elapsed</dt><dd>{record?.elapsed_seconds == null ? '—' : `${record.elapsed_seconds.toFixed(1)}s`}</dd></div></dl><span className="model-note">Provisional model · one development workflow</span></div>
        <div className="scope-card"><span className="small-label">KEEP THE CLAIM IN SCOPE</span><p>A measured difference is a starting point. The full published disagreement and theorem remain unresolved.</p><button className="text-button" onClick={() => setView('evidence')}>See evidence & limitations <Icon name="arrow" size={13} /></button></div>
      </aside></div></>}
      <footer className="page-footer"><span><span className="local-dot" /> Evidence first. Every attempt preserved.</span><span>CounterLab / Nebius × NVIDIA</span></footer></main>
    </div>
    <Modal open={launch} close={() => { if (!starting) setLaunch(false); }} label="Review and start an investigation"><span className="overline">REVIEW BEFORE RUNNING</span><h2>Start a new investigation.</h2><p className="modal-intro">Nemotron will choose among three reviewed paging cases, commit predictions, and use mathematical checks and measured results to guide one follow-up.</p><div className="launch-protocol"><div><span>Changed factor</span><strong>History-update timing</strong></div><div><span>Fixed settings</span><strong>Seed 0 · τ 0 · empty cache</strong></div><div><span>Execution scope</span><strong>Reviewed local adapter · up to 2 tests</strong></div><div><span>Model</span><strong>NVIDIA Nemotron 3 Ultra on Nebius</strong></div></div>
      <details className="approved-inputs"><summary>Inspect the three approved input cases</summary>{record?.protocol.cases.map(item => <p key={item.case_id}>{item.case_id.replace("_", " ")}: {item.capacity} cache slots · {item.request_count} requests</p>)}<pre>{JSON.stringify(record?.protocol.cases, null, 2)}</pre></details><label className="field-label" htmlFor="output-cap">Output allowance per model request</label><select id="output-cap" value={cap} onChange={event => setCap(Number(event.target.value))}><option value={8192}>8,192 tokens · default allowance</option><option value={4096}>4,096 tokens · may finish before a complete plan</option></select><p className="field-help">At most {workspace?.maximum_inference_requests ?? 2} planning requests: up to {number(cap * (workspace?.maximum_inference_requests ?? 2))} output tokens, plus input tokens. The factual report uses no additional model request. This is a token allowance, not a dollar spending limit.</p>
      <label className="consent"><input type="checkbox" checked={consent} onChange={event => setConsent(event.target.checked)} /><span>I approve this reviewed protocol and using my Nebius credits for this bounded investigation.</span></label><p className="field-help">Closing the page does not cancel a running investigation. There are no automatic retries.</p>{startError && <div className="error-banner" role="alert">{startError}</div>}<button className="button button-primary full-width" disabled={!consent || starting} onClick={start}>{starting ? <><span className="spinner" /> Starting…</> : <>Start investigation <Icon name="arrow" /></>}</button>
    </Modal>
    <Modal open={drawer} close={() => setDrawer(false)} label="Evidence record" drawer><span className="overline">EVIDENCE DRAWER</span><h2>Inspect the record.</h2><p className="modal-intro">Proposals are model output. {isEvidenceBuild ? 'Measurements come from the reviewed runner and were replayed when packaged.' : 'Measurements come from the reviewed runner and are replayed before display.'}</p>{record && <><div className="drawer-section"><span className="small-label">PROTOCOL HASH</span><code className="block-code">{record.protocol.sha256}</code></div><div className="drawer-section"><span className="small-label">REVIEWED PROTOCOL AND INPUTS</span><pre>{JSON.stringify(record.protocol, null, 2)}</pre></div><div className="drawer-section"><span className="small-label">NUMERICAL EVIDENCE</span><pre>{JSON.stringify(record.attempts.filter(attempt => attempt.evidence).map(attempt => attempt.evidence), null, 2)}</pre></div><div className="drawer-section"><span className="small-label">VERIFICATION</span><pre>{JSON.stringify(record.provenance, null, 2)}</pre></div><div className="drawer-section"><span className="small-label">EXPERIMENT EXECUTION</span><p>{record.attempts.some(attempt => attempt.execution) ? "Execution receipts identify the worker image and resource limits for this run." : "This earlier run predates the isolated worker. Numerical replay remains available."}</p><pre>{JSON.stringify(record.attempts.filter(attempt => attempt.execution).map(attempt => attempt.execution), null, 2)}</pre></div><div className="drawer-section"><span className="small-label">LIMITATIONS</span><ul>{record.limits.map(limit => <li key={limit}>{limit}</li>)}</ul></div>{record.export_available && <a className="button button-primary full-width" href={evidenceHref(`/api/investigations/${record.id}/export`)}><Icon name="download" /> Download evidence & replay</a>}</>}</Modal>
  </div>;
}

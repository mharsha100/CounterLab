import { useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { evidenceHref, isEvidenceBuild } from '../access';
import { failureMessage, plural } from '../format';
import { navigateTo, setParam, useParam } from '../navigation';
import { ExperimentView, Verdict, notMeasuredReason } from './experiment';
import {
  action, active, api, ApiError, canWrite, duration, exact, kilobytes, num, refreshLab, runTitle, setDraft, shortModel, toast, useLab,
  type Run,
} from './data';
import { AppLink, Badge, copyText, Dialog, Empty, Icon, Skeleton, Spinner, StateBadge } from './ui';

const STEPS = ['Read', 'Design & commit', 'Check', 'Run twice', 'Report'];
const SETTINGS_ERRORS = new Set(['provider_http_401', 'provider_http_403', 'model_not_in_catalog', 'no_nemotron_model_in_catalog', 'sandbox_unavailable', 'provider_http_402']);

function finishedSteps(run: Run) {
  const designed = run.experiments.some(e => e.plan);
  const checked = run.experiments.some(e => e.attempts?.some(a => a.admission));
  const measured = run.experiments.some(e => e.evaluation);
  return [Boolean(run.inputs), designed, checked, measured, Boolean(run.summary) && measured];
}
function modeLabel(run: Run) {
  if (run.provider_mode === 'simulated_provider') return 'Simulated planning';
  return run.kind === 'recorded' ? 'Recorded · Nemotron' : 'Nemotron on Nebius';
}

function ProgressRail({ run, elapsed }: { run: Run; elapsed: number }) {
  const live = active(run.state);
  const current = live ? Math.min(run.step ?? 0, 4) : 5;
  const finished = live ? null : finishedSteps(run);
  return <section className={`rail ${live ? 'rail-live' : ''}`} aria-label="Progress">
    <ol>{STEPS.map((label, index) => {
      const done = finished ? finished[index] : index < current;
      const missed = finished ? !finished[index] : false;
      const now = live && index === current;
      return <li key={label} className={done ? 'done' : missed ? 'missed' : now ? 'now' : ''}>
        <span className="rail-node" aria-hidden="true">{done ? <Icon name="check" size={13} /> : now ? <span className="pulse" /> : index + 1}</span>
        <span className="rail-label">{label}</span>
        <span className="visually-hidden">{done ? ' (done)' : missed ? ' (not reached)' : now ? ' (in progress)' : ''}</span>
      </li>;
    })}</ol>
    {live && <div className="rail-status" role="status" aria-live="polite">
      <Spinner /><div><strong>{run.phase}</strong>{run.notice && <span className="rail-notice">{run.notice}</span>}</div>
      <span className="rail-time">{duration(elapsed)}</span>
    </div>}
  </section>;
}

// The code-written finding always ends with the bet sentence and the scope note; the card shows the bet as a badge.
function summaryLines(finding: string[]): string[] {
  const lines = finding.length > 2 ? finding.slice(0, -2) : finding.slice(0, 1);
  return lines.length ? lines : finding.slice(0, 1);
}

function Overview({ run, openTab }: { run: Run; openTab: (tab: string) => void }) {
  const live = active(run.state);
  const simulated = run.provider_mode === 'simulated_provider';
  const designed = run.experiments.filter(e => e.plan);
  const measured = designed.filter(e => e.evaluation);
  return <div className="stack">
    {designed.length === 0 && live && <section className="panel"><p className="label">Waiting for the first design</p>
      <p className="small-text">Nemotron is reading your inputs and designing an experiment. Nothing runs until its plan and predictions are committed.</p><Skeleton lines={3} /></section>}
    {designed.length === 0 && !live && <Empty icon="activity" title="No experiment was designed">The investigation stopped before an experiment was committed. The Activity tab shows each request and why it stopped.</Empty>}
    {designed.map(experiment => {
      const plan = experiment.plan!, evaluation = experiment.evaluation;
      return <section key={experiment.index} className="panel summary-card">
        <div className="summary-head"><div><p className="eyebrow">Experiment {experiment.index}{experiment.index > 1 ? ' · follow-up' : ''}</p><h2>{plan.title}</h2></div>
          {evaluation ? <Badge tone={evaluation.bet.outcome === 'held' ? 'good' : evaluation.bet.outcome === 'failed' ? 'bad' : 'neutral'}>
            {simulated ? 'Committed bet' : 'Nemotron’s bet'} ({evaluation.bet.explanation}) {evaluation.bet.outcome}</Badge>
            : <Badge tone={live ? 'run' : 'warn'} dot>{live ? 'In progress' : experiment.status === 'not_measured' ? 'Not measured' : 'Not finished'}</Badge>}</div>
        <p className="small-text"><strong>Factor varied:</strong> {plan.factor}</p>
        {!evaluation && !live && experiment.status === 'not_measured' && <p className="finding-line not-measured">{notMeasuredReason(experiment)}</p>}
        {evaluation && <><div className="badge-row">{evaluation.explanations.map(item => <span key={item.id} className="explanation-chip"><strong>{item.id}</strong> <Verdict status={item.status} /></span>)}</div>
          <div className="finding-lines">{summaryLines(evaluation.finding).map((line, at) => <p key={at} className="finding-line">{line}</p>)}</div></>}
        <button type="button" className="btn btn-quiet" onClick={() => openTab(`e${experiment.index}`)}>Open experiment {experiment.index} <Icon name="arrow" /></button>
      </section>;
    })}
    {measured.length >= 2 && <section className="panel"><h2 className="panel-title">What each experiment settled</h2>
      <div className="table-scroll" tabIndex={0} role="region" aria-label="Experiment comparison"><table className="data-table">
        <thead><tr><th scope="col">Experiment</th><th scope="col">Factor varied</th><th scope="col">Consistent</th><th scope="col">Contradicted</th><th scope="col">Bet</th></tr></thead>
        <tbody>{measured.map(e => <tr key={e.index}><th scope="row">{e.index}. {e.plan!.title}</th><td>{e.plan!.factor}</td>
          <td>{e.evaluation!.explanations.filter(x => x.status === 'consistent').map(x => x.id).join(', ') || '—'}</td>
          <td>{e.evaluation!.explanations.filter(x => x.status === 'contradicted').map(x => x.id).join(', ') || '—'}</td>
          <td className="nowrap">{e.evaluation!.bet.explanation}: {e.evaluation!.bet.outcome}</td></tr>)}</tbody>
      </table></div></section>}
    {run.inputs && <section className="panel inline-summary"><Icon name="file" /><p>{simulated ? 'The simulated planner' : 'Nemotron'} read {plural(run.inputs.papers.length, 'paper')} and {plural(run.inputs.code_files.length, 'code file')}
      {run.context?.code_files_not_shown.length ? ` (${run.context.code_files_not_shown.length} listed by name only)` : ''}.</p>
      <button type="button" className="btn btn-quiet" onClick={() => openTab('inputs')}>Inputs <Icon name="arrow" /></button></section>}
  </div>;
}

function Inputs({ run }: { run: Run }) {
  if (!run.inputs) return <Empty icon="file" title="Inputs are still being read">They appear here once CounterLab has unpacked them.</Empty>;
  const links = run.request?.links;
  return <div className="stack">
    {run.request?.reused_inputs_from && <p className="note"><Icon name="rerun" /> These inputs were reused from <AppLink route="run" params={{ id: run.request.reused_inputs_from }}>an earlier investigation</AppLink>.</p>}
    <section className="panel"><h2 className="panel-title">Papers <span className="count">{run.inputs.papers.length}</span></h2>
      {run.inputs.papers.length ? <ul className="file-list">{run.inputs.papers.map(paper => <li key={paper.name}><Icon name="file" /><span className="file-name">{paper.name}</span>
        <span className="file-meta">{paper.pages ? `${paper.pages} pages · ` : ''}{paper.characters.toLocaleString()} characters{paper.source !== 'upload' ? ` · ${paper.source}` : ''}</span></li>)}</ul>
        : <p className="small-text">No paper. Nemotron worked from the code and your question.</p>}</section>
    <section className="panel"><h2 className="panel-title">Code <span className="count">{run.inputs.code_files.length}</span></h2>
      {run.inputs.code_files.length ? <ul className="file-list code-files">{run.inputs.code_files.slice(0, 300).map(file => <li key={file.path}><code>{file.path}</code><span className="file-meta">{kilobytes(file.bytes)}</span></li>)}
        {run.inputs.code_files.length > 300 && <li className="small-text">…and {run.inputs.code_files.length - 300} more</li>}</ul>
        : <p className="small-text">No code. Nemotron implemented the described method from the paper, and the record says so.</p>}
      {run.context && run.context.code_files_not_shown.length > 0 && <p className="small-text">{plural(run.context.code_files_not_shown.length, 'file')} did not fit in Nemotron’s context and {run.context.code_files_not_shown.length === 1 ? 'was' : 'were'} listed by name only.</p>}
    </section>
    {(links?.paper_url || links?.code_url) && <section className="panel"><h2 className="panel-title">Links</h2><ul className="file-list">
      {links?.paper_url && <li><Icon name="link" /><a href={links.paper_url} target="_blank" rel="noreferrer">{links.paper_url}</a></li>}
      {links?.code_url && <li><Icon name="link" /><a href={links.code_url} target="_blank" rel="noreferrer">{links.code_url}</a></li>}</ul></section>}
    {run.inputs.notes.length > 0 && <section className="panel"><h2 className="panel-title">Notes from reading the inputs</h2><ul className="plain-list">{run.inputs.notes.map(note => <li key={note}>{note}</li>)}</ul></section>}
    <p className="small-text">Uploaded documents are passed to Nemotron as data; instructions inside them are not followed.</p>
  </div>;
}

function Activity({ run }: { run: Run }) {
  const who = run.provider_mode === 'simulated_provider' ? 'Planning requests (simulated)' : 'Nemotron requests';
  const calls = run.summary?.calls ?? [];
  const events = run.summary?.provider_events ?? run.provider_events ?? [];
  return <div className="stack">
    {run.connection && <section className="panel"><h2 className="panel-title">Model</h2>
      <p className="small-text">Used <strong>{run.connection.model ?? '—'}</strong>{run.connection.model_note === 'preferred_model_unavailable' ? `, because ${run.connection.preferred_model} was not in your Token Factory catalog` : ''}. Catalog checked {exact(run.connection.checked_at)}.</p></section>}
    <section className="panel"><h2 className="panel-title">{who} <span className="count">{calls.length}</span></h2>
      {calls.length ? <div className="table-scroll" tabIndex={0} role="region" aria-label={who}><table className="data-table">
        <thead><tr><th scope="col">#</th><th scope="col">Purpose</th><th scope="col">Outcome</th><th scope="col">Prompt tokens</th><th scope="col">Output tokens</th><th scope="col">Time</th></tr></thead>
        <tbody>{calls.map((call, index) => <tr key={index}><td className="num">{index + 1}</td><td>{call.purpose.replaceAll('_', ' ')}</td>
          <td>{call.outcome === 'ok' ? <Badge tone="good">✓ ok</Badge> : <Badge tone="warn" title={failureMessage(call.outcome)}>{call.outcome.replaceAll('_', ' ')}</Badge>}</td>
          <td className="num">{num(call.usage?.prompt_tokens)}</td><td className="num">{num(call.usage?.completion_tokens)}</td><td className="num">{duration(call.elapsed_seconds)}</td></tr>)}</tbody>
      </table></div> : <p className="small-text">{active(run.state) ? 'No completed request yet.' : 'No request reached Nemotron.'}</p>}</section>
    <section className="panel"><h2 className="panel-title">Connection events <span className="count">{events.length}</span></h2>
      {events.length ? <ul className="event-list">{events.map((event, index) => <li key={index}><span className="mono-meta">{event.at.replace('T', ' ').replace('Z', ' UTC')}</span>
        {event.kind === 'retry' ? <span>Temporary error <code>{event.code}</code> on attempt {event.attempt}; retried after {event.delay_seconds} s.</span>
          : <span>Nebius rejected the {event.from} response format (HTTP {event.status}); switched to {event.to?.replace('_', ' ')} output.</span>}</li>)}</ul>
        : <p className="small-text">{active(run.state) ? 'None so far.' : 'None. Every request went through on the first attempt.'}</p>}</section>
  </div>;
}

function Record({ run }: { run: Run }) {
  return <div className="stack">
    <section className="panel"><h2 className="panel-title">Integrity</h2>
      {run.verification ? <ul className="check-list"><li><Icon name="check" /> {plural(run.verification.files_verified, 'file')} match their SHA-256 seal</li>
        <li><Icon name="check" /> {plural(run.verification.evaluations_recomputed, 'finding')} recomputed from the saved sandbox rows</li></ul>
        : <p className="small-text">{active(run.state) ? 'The record is sealed and checked when the investigation finishes.' : 'This record has no seal, so it cannot be exported.'}</p>}</section>
    {run.export_available && <section className="panel export-card"><div><h2 className="panel-title">Replay package</h2>
      <p className="small-text">The inputs, every committed plan, every sandbox row and every finding. Recheck it anywhere with standard-library Python: no key, Docker or network.</p>
      <pre className="cmd">python replay.py          # verify hashes, recompute findings{'\n'}python replay.py --rerun  # also re-execute the experiments</pre></div>
      <a className="btn btn-primary" href={evidenceHref(`/api/open-investigations/${run.id}/export`)} download><Icon name="download" /> Download replay package</a></section>}
    <section className="panel"><h2 className="panel-title">Identifiers</h2><dl className="kv">
      <div><dt>Investigation</dt><dd><code>{run.id}</code> <button type="button" className="icon-btn" aria-label="Copy investigation ID" onClick={() => copyText(run.id, 'Investigation ID copied')}><Icon name="copy" size={14} /></button></dd></div>
      {run.experiments.filter(e => e.plan_sha256).map(e => <div key={e.index}><dt>Plan {e.index} SHA-256</dt><dd><code>{e.plan_sha256}</code></dd></div>)}
    </dl></section>
  </div>;
}

export default function RunPage({ id }: { id: string }) {
  const { contract } = useLab();
  const [run, setRun] = useState<Run | null>(null);
  const [error, setError] = useState('');
  const [missing, setMissing] = useState(false);
  const [now, setNow] = useState(() => Date.now());
  const [confirmStop, setConfirmStop] = useState(false);
  const [confirmRemove, setConfirmRemove] = useState(false);
  const [busy, setBusy] = useState('');
  const tabParam = useParam('tab');
  const tabRefs = useRef<Record<string, HTMLButtonElement | null>>({});

  useEffect(() => {
    let cancelled = false, timer: ReturnType<typeof setTimeout>;
    setRun(null); setError(''); setMissing(false);
    async function load() {
      try {
        const next = await api<Run>(`/api/open-investigations/${id}`);
        if (cancelled) return;
        setRun(next); setError('');
        if (active(next.state)) timer = setTimeout(load, 1500);
        else refreshLab();
      } catch (cause) {
        if (cancelled) return;
        if (cause instanceof ApiError && cause.status === 404) setMissing(true);
        else { setError(cause instanceof Error ? cause.message : 'The investigation could not be loaded.'); timer = setTimeout(load, 4000); }
      }
    }
    load();
    return () => { cancelled = true; clearTimeout(timer); };
  }, [id]);
  const live = active(run?.state);
  useEffect(() => {
    if (!live) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [live]);
  useEffect(() => { if (run) document.title = `${runTitle({ title: run.overview?.title, question: run.request?.question ?? '' }) || 'Investigation'} — CounterLab`; }, [run?.overview?.title, run?.request?.question]);

  if (missing) return <div className="page"><Empty icon="search" title="Investigation not found" action={<AppLink route="runs" className="btn btn-secondary">All investigations</AppLink>}>
    It may have been removed from the list, or the link is incomplete.</Empty></div>;
  if (!run) return <div className="page"><nav className="crumbs" aria-label="Breadcrumb"><AppLink route="runs">Investigations</AppLink></nav>
    {error ? <div className="alert alert-bad" role="alert"><Icon name="alert" /><div><strong>Could not load this investigation.</strong> {error} Retrying…</div></div> : <><Skeleton lines={2} /><Skeleton lines={5} /></>}</div>;

  const question = run.request?.question ?? '';
  const title = runTitle({ title: run.overview?.title, question });
  const tabs = [['overview', 'Overview'], ...run.experiments.filter(e => e.plan || e.attempts?.length).map(e => [`e${e.index}`, `Experiment ${e.index}`]), ['inputs', 'Inputs'], ['activity', 'Activity'], ['record', 'Record']];
  const tab = tabs.some(([key]) => key === tabParam) ? tabParam : 'overview';
  const writable = canWrite(contract) && run.kind === 'live';
  const started = run.summary?.started_at ?? run.created_at;
  const elapsed = live ? (now - new Date(started).getTime()) / 1000 : run.overview?.duration_seconds ?? null;
  const requests = run.summary ? `${run.summary.model_calls} of ${run.summary.maximum_model_calls}` : live ? 'In progress' : '—';
  const retries = run.summary?.automatic_retries ?? 0;
  const simulated = run.provider_mode === 'simulated_provider';

  function openTab(next: string) {
    setParam('tab', next === 'overview' ? '' : next);
    requestAnimationFrame(() => tabRefs.current[next]?.focus());
  }
  function tabKeys(event: KeyboardEvent<HTMLDivElement>) {
    const index = tabs.findIndex(([key]) => key === tab);
    const next = event.key === 'ArrowRight' ? index + 1 : event.key === 'ArrowLeft' ? index - 1 : event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : null;
    if (next === null) return;
    event.preventDefault();
    openTab(tabs[(next + tabs.length) % tabs.length][0]);
  }
  async function stop() {
    setBusy('stop');
    try { await action(`/api/open-investigations/${run!.id}/cancel`, 'stop-investigation'); toast('Stopping the investigation. Saved steps stay in the record.'); setConfirmStop(false); }
    catch (cause) { toast(cause instanceof Error ? cause.message : 'The investigation could not be stopped.', 'bad'); }
    finally { setBusy(''); }
  }
  async function remove() {
    setBusy('remove');
    try { await action(`/api/open-investigations/${run!.id}/archive`, 'archive-investigation'); await refreshLab(); toast('Removed from the list. The record stays on disk.', 'good'); navigateTo('runs'); }
    catch (cause) { toast(cause instanceof Error ? cause.message : 'The investigation could not be removed.', 'bad'); setConfirmRemove(false); }
    finally { setBusy(''); }
  }
  function runAgain() {
    setDraft({ files: [], question, allowance: run!.request?.max_output_tokens, followUp: run!.request?.follow_up });
    navigateTo('lab', { from: run!.id });
  }

  return <div className="page run-page">
    <nav className="crumbs" aria-label="Breadcrumb"><AppLink route="runs">Investigations</AppLink><Icon name="chevron" size={12} /><span aria-current="page">{title.length > 60 ? `${title.slice(0, 58)}…` : title}</span></nav>
    <header className="run-head">
      <div className="run-head-text">
        <div className="meta-row"><StateBadge state={run.state} /><Badge tone={run.provider_mode === 'simulated_provider' ? 'warn' : 'neutral'}>{modeLabel(run)}</Badge>
          <span>{exact(run.created_at)}</span>{run.overview?.model && !simulated && <span>{shortModel(run.overview.model)}</span>}</div>
        <h1 className="page-title" tabIndex={-1}>{title}</h1>
        {title !== question && <p className="run-question">{question}</p>}
      </div>
      <div className="head-actions">
        {live && writable && <button type="button" className="btn btn-danger" onClick={() => setConfirmStop(true)} disabled={Boolean(run.notice?.startsWith('Stopping'))}><Icon name="stop" /> {run.notice?.startsWith('Stopping') ? 'Stopping…' : 'Stop'}</button>}
        {!live && canWrite(contract) && run.inputs && <button type="button" className="btn btn-secondary" onClick={runAgain}><Icon name="rerun" /> Run again</button>}
        {run.export_available && <a className="btn btn-secondary" href={evidenceHref(`/api/open-investigations/${run.id}/export`)} download><Icon name="download" /> Replay package</a>}
        <button type="button" className="icon-btn bordered" onClick={() => copyText(window.location.href, 'Link copied')} aria-label="Copy link to this investigation" title="Copy link"><Icon name="link" /></button>
        {writable && !live && <button type="button" className="icon-btn bordered" onClick={() => setConfirmRemove(true)} aria-label="Remove from the list" title="Remove from the list"><Icon name="archive" /></button>}
      </div>
    </header>

    {run.provider_mode === 'simulated_provider' && <div className="alert alert-warn" role="note"><Icon name="alert" /><div><strong>Simulated planning.</strong> The plans in this record were written by the CounterLab developers to exercise the pipeline; they are not Nemotron output. The sandbox runs, checks and report are real.</div></div>}
    <ProgressRail run={run} elapsed={elapsed ?? 0} />
    {run.error && run.error !== 'cancelled_by_user' && <div className="alert alert-bad" role="alert"><Icon name="alert" /><div>
      <strong>{run.phase}.</strong> {run.error === 'intake_error' || run.error === 'sandbox_unavailable' ? run.detail : failureMessage(run.error)} Saved steps are kept in the record.
      <div className="alert-actions">{SETTINGS_ERRORS.has(run.error) ? <AppLink route="settings" className="btn btn-secondary">Open Settings</AppLink>
        : canWrite(contract) && run.inputs ? <button type="button" className="btn btn-secondary" onClick={runAgain}><Icon name="rerun" /> Run again</button> : null}</div></div></div>}
    {run.state === 'cancelled' && <div className="alert" role="status"><Icon name="stop" /><div><strong>Stopped.</strong> You stopped this investigation. Everything committed or measured before that is kept and checkable.</div></div>}
    {run.summary?.review_reason && !run.error && run.state !== 'cancelled' && <div className="alert alert-warn" role="status"><Icon name="alert" /><div><strong>Review needed.</strong> {failureMessage(run.summary.review_reason)}</div></div>}

    <div className="run-layout">
      <div className="run-main">
        <div className="tabs" role="tablist" aria-label="Investigation sections" onKeyDown={tabKeys}>
          {tabs.map(([key, label]) => <button key={key} ref={element => { tabRefs.current[key] = element; }} type="button" role="tab" id={`tab-${key}`} aria-selected={tab === key}
            aria-controls={`panel-${key}`} tabIndex={tab === key ? 0 : -1} className="tab" onClick={() => openTab(key)}>{label}</button>)}
        </div>
        <div className="tab-panel" role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
          {tab === 'overview' && <Overview run={run} openTab={openTab} />}
          {tab.startsWith('e') && run.experiments.filter(e => `e${e.index}` === tab).map(e => <ExperimentView key={e.index} experiment={e} recorded={run.kind === 'recorded'} simulated={simulated} />)}
          {tab === 'inputs' && <Inputs run={run} />}
          {tab === 'activity' && <Activity run={run} />}
          {tab === 'record' && <Record run={run} />}
        </div>
      </div>
      <aside className="run-side" aria-label="Investigation details">
        <h2 className="side-title">Details</h2>
        <dl className="kv">
          <div><dt>Status</dt><dd><StateBadge state={run.state} /></dd></div>
          <div><dt>Model</dt><dd>{simulated ? 'Simulated planner (developer-written plans)' : run.overview?.model ?? run.connection?.model ?? contract?.model ?? '—'}</dd></div>
          <div><dt>Provider</dt><dd>{run.provider_mode === 'simulated_provider' ? 'Simulated (no network)' : 'Nebius Token Factory'}</dd></div>
          <div><dt>{simulated ? 'Planning requests' : 'Nemotron requests'}</dt><dd>{requests}{retries ? ` · ${plural(retries, 'automatic retry', 'automatic retries')}` : ''}</dd></div>
          <div><dt>Tokens</dt><dd>{num(run.summary?.usage?.total_tokens)}</dd></div>
          <div><dt>{live ? 'Elapsed' : 'Duration'}</dt><dd>{duration(elapsed)}</dd></div>
          <div><dt>Sandbox</dt><dd>{run.summary?.sandbox ? (run.summary.sandbox.isolation === 'docker_no_network' ? 'Docker · no network' : run.summary.sandbox.mode.replaceAll('_', ' ')) : '—'}</dd></div>
          {run.summary?.response_format && <div><dt>Response format</dt><dd>{run.summary.response_format === 'strict' ? 'Strict JSON schema' : run.summary.response_format === 'relaxed' ? 'Relaxed JSON schema' : 'JSON mode'}</dd></div>}
          <div><dt>Record</dt><dd>{run.verification ? 'Sealed and verified' : live ? 'Sealed when finished' : 'Not sealed'}</dd></div>
        </dl>
        {isEvidenceBuild && <p className="small-text">This hosted demo shows a recorded investigation. Download the source to run your own.</p>}
      </aside>
    </div>

    <Dialog open={confirmStop} onClose={() => setConfirmStop(false)} title="Stop this investigation?" size="s"
      footer={<><button type="button" className="btn btn-secondary" onClick={() => setConfirmStop(false)}>Keep running</button>
        <button type="button" className="btn btn-danger" onClick={stop} disabled={busy === 'stop'}>{busy === 'stop' ? 'Stopping…' : 'Stop investigation'}</button></>}>
      <p>CounterLab stops after the current step: a pending Nemotron request is abandoned and a running sandbox is shut down. Everything already committed or measured stays in the record.</p>
    </Dialog>
    <Dialog open={confirmRemove} onClose={() => setConfirmRemove(false)} title="Remove from the list?" size="s"
      footer={<><button type="button" className="btn btn-secondary" onClick={() => setConfirmRemove(false)}>Cancel</button>
        <button type="button" className="btn btn-danger" onClick={remove} disabled={busy === 'remove'}>Remove</button></>}>
      <p>The investigation disappears from your lists. Its sealed record stays in <code>artifacts/runs/open</code> on this computer.</p>
    </Dialog>
  </div>;
}

import { projectFetch, evidenceHref, isEvidenceBuild } from './access';
import { useEffect, useRef, useState } from 'react';
import type { Review } from './PredictionReview';

type Test = { test_id: string; role: string; seed_index: number; profiles: number[]; changed_factors: string[] };
type Task = { question: string; exposure: string; options: Test[]; held_fixed: string[]; limits: string[] };
type Contract = { workflow_version?: string; read_only?: boolean; task: Task; model: string; provider_mode: string; input: unknown };
type Profile = { history: string; tau: number; seed: number; misses_after_warmup: number; gate_credits: number; trace_sha256: string };
type Evidence = { evidence_id: string; profiles: Profile[]; warmup_length: number; input_sha256: string; seed: number };
type Attempt = { number: number; plan: { test_id: string; hypothesis: string; predict_gate_difference: boolean; predict_miss_difference: boolean };
  prediction_review?: Review; decision?: { accepted: boolean; reason: string; explanation: string }; unverified_execution_artifacts?: string[];
  admission: { accepted: boolean; answers_target: boolean; explanation: string }; measurement: Evidence | null; predictions_correct: boolean | null };
type SourceRun = { workflow_version?: string; id: string; state: string; phase: string; error: string | null; provider_mode: string; export_available: boolean; attempts: Attempt[];
  summary?: { workflow_version?: string; prediction_rejections?: number; contract_rejections?: number; inference_requests: number; usage: { total_tokens?: number }; review_reason?: string };
  evidence_report?: { outcome: string; summary: string; measured_tests: number; control_measurements: number; report_sha256: string; all_measurements: unknown[] } };
type Item = { id: string; state: string; created_at: string; adapter?: string; provider_mode: string };
const active = (state: string) => ['queued', 'running'].includes(state);
async function read<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await projectFetch(url, init);
  const body = await response.json();
  if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'The source investigation could not be loaded.');
  return body;
}

export default function SourceInvestigator() {
  const [contract, setContract] = useState<Contract | null>(null);
  const [items, setItems] = useState<Item[]>([]);
  const [selected, setSelected] = useState('');
  const [record, setRecord] = useState<SourceRun | null>(null);
  const [consent, setConsent] = useState(false);
  const [cap, setCap] = useState(8192);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState('');
  const requestId = useRef('');
  const simulated = contract?.provider_mode === 'simulated_provider';
  async function listing() {
    const result = await read<{ items: Item[] }>('/api/investigations');
    const source = result.items.filter(row => row.adapter === 'source');
    setItems(source);
    return source;
  }
  useEffect(() => {
    let cancelled = false;
    Promise.all([read<Contract>('/api/source-investigator-v2'), read<{ items: Item[] }>('/api/investigations')])
      .then(([next, rows]) => { if (!cancelled) { setContract(next); const source = rows.items.filter(row => row.adapter === 'source'); setItems(source); setSelected(source[0]?.id || ''); } })
      .catch(cause => { if (!cancelled) setError(cause.message); });
    return () => { cancelled = true; };
  }, []);
  useEffect(() => {
    if (!selected) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    setRecord(null);
    async function refresh() {
      try {
        const next = await read<SourceRun>(`/api/source-investigations/${selected}`);
        if (cancelled) return;
        setRecord(next); setError('');
        if (active(next.state)) timer = setTimeout(refresh, 1200);
        else await listing();
      } catch (cause) { if (!cancelled) setError(cause instanceof Error ? cause.message : 'Source record unavailable.'); }
    }
    refresh();
    return () => { cancelled = true; clearTimeout(timer); };
  }, [selected]);
  async function start() {
    if (!consent || starting) return;
    if (!requestId.current) requestId.current = crypto.randomUUID().replaceAll('-', '');
    setStarting(true); setError('');
    try {
      const row = await read<{ id: string }>('/api/source-investigations-v2', { method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CounterLab-Action': 'start-investigation' },
        body: JSON.stringify({ request_id: requestId.current, confirm_credit_use: true, max_output_tokens: cap }) });
      setSelected(row.id); setConsent(false); requestId.current = ''; await listing();
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not start the source investigation.'); }
    finally { setStarting(false); }
  }
  return <section className="source-investigator study-panel" aria-labelledby="source-investigator-title">
    <div className="section-title"><div><span className="overline">SOURCE INVESTIGATOR · WORKFLOW V2</span><h3 id="source-investigator-title">{contract?.read_only ? 'Inspect source investigations.' : 'Check the prediction before running the test.'}</h3></div><span className="badge">At most two planning calls</span></div>
    <p className="study-caption">The model commits predictions. Input-only checks reject contradictions before the worker starts; a rejection supplies no measured counts. The model can use that feedback to choose an untried test. Every admitted test runs twice in isolated containers at 150,000 requests. A host replay checks the complete result. Counts and the final report are derived from those measurements.</p>
    <p className="study-caption">This is the previously explored source slice above. The check rules out some impossible predictions; passing it does not prove correctness. The frozen model scores remain unchanged. A new evaluation is needed to measure this version’s planning quality.</p>
    {simulated && <div className="study-note"><strong>Simulated planning · integration check</strong><p>No Nebius requests are sent by this preview. Numerical experiments still execute. This is not a model-performance result.</p></div>}
    {contract && <><details className="study-details"><summary>Review the four allowed tests and source settings</summary><div className="source-test-options">{contract.task.options.map(test => <div key={test.test_id}><strong>{test.test_id.replaceAll('_', ' ')}</strong><p>{test.role === 'repeat_control' ? 'Repeat the same profile in separate containers. Checks replay consistency; cannot answer the history question.' : test.changed_factors.includes('history_refresh') ? `Matched history intervention · algorithm seed ${900 + test.seed_index}.` : 'Changes the budget reset. The admission check rejects this option for the history question.'}</p></div>)}</div><pre>{JSON.stringify(contract.input, null, 2)}</pre></details>
      {contract.read_only ? <div className="study-note"><strong>Read-only demonstration</strong><p>Saved evidence is available. {isEvidenceBuild ? 'This build contains recorded results only; it has no live backend.' : 'Starting source investigations is disabled by the server.'}</p></div> : <div className="source-start"><label className="field-label" htmlFor="source-output-cap">Output allowance per planning call</label><select id="source-output-cap" value={cap} disabled={starting} onChange={event => { setCap(Number(event.target.value)); requestId.current = ''; setConsent(false); }}><option value={8192}>8,192 tokens</option><option value={4096}>4,096 tokens</option></select>
      <p className="study-caption">Up to {(cap * 2).toLocaleString()} output tokens plus input tokens, two accepted tests and four container launches. No automatic retries or final reporting call. This token allowance is not a dollar spending limit.</p>
      <label className="source-consent"><input type="checkbox" checked={consent} onChange={event => setConsent(event.target.checked)} />{simulated ? 'Run this simulated planning integration check.' : 'I approve using my Nebius promotional credits for this bounded source investigation.'}</label>
      <button className="button button-primary" disabled={!consent || starting || (record ? active(record.state) : false)} onClick={start}>{starting ? 'Starting…' : 'Start source investigation →'}</button></div>}</>}
    {error && <p className="error-banner" role="alert">{error}</p>}
    {items.length > 0 && <label className="source-history">Saved source investigations<select value={selected} onChange={event => setSelected(event.target.value)}>{items.map(row => <option key={row.id} value={row.id}>{new Date(row.created_at).toLocaleString()} · {row.state}{row.provider_mode === 'simulated_provider' ? ' · simulated planning' : ''}</option>)}</select></label>}
    {selected && !record && <p className="study-caption" role="status">{isEvidenceBuild ? 'Checking recorded evidence…' : 'Verifying the saved source record and replaying its measurements…'}</p>}
    {record && <div className="source-run"><div className="section-title"><h3>{record.phase}</h3><span className="badge">{record.workflow_version ? 'Prediction gate v2' : 'Historical v1'}</span><span className="badge">{record.provider_mode === 'simulated_provider' ? 'Simulated planning' : 'Nebius · Nemotron'}</span></div>
      {active(record.state) && <p role="status">The bounded investigation is running. Reopening this saved run does not start another.</p>}
      {record.error && <p role="alert">The investigation stopped: {record.error.replaceAll('_', ' ')}. It was not automatically retried.</p>}
      {record.summary?.review_reason && <p role="alert">Review needed: {record.summary.review_reason.replaceAll('_', ' ')}. Accepted measurements are retained.</p>}
      {record.summary?.prediction_rejections !== undefined && <p className="study-caption">Prediction rejections before worker execution: {record.summary.prediction_rejections} · Contract rejections: {record.summary.contract_rejections}. These decisions are not measured outcomes.</p>}
      {record.attempts.map(attempt => <article className="source-attempt" key={attempt.number}><span className="overline">PROPOSAL {attempt.number} · {attempt.plan.test_id.replaceAll('_', ' ')}</span>{attempt.decision && <span className="overline">CHECK BEFORE EXECUTION</span>}<p><strong>{attempt.decision?.explanation || attempt.admission.explanation}</strong></p>
        <details className="study-details"><summary>Model hypothesis · unverified proposal</summary><p>{attempt.plan.hypothesis}</p></details>
        <p className="study-caption">Precommitted: gate credits {attempt.plan.predict_gate_difference ? 'differ' : 'agree'}; misses {attempt.plan.predict_miss_difference ? 'differ' : 'agree'}.</p>
        {attempt.prediction_review && <div className={`source-preflight ${attempt.decision?.accepted ? '' : 'source-preflight-rejected'}`}><strong>{attempt.decision?.reason === 'prediction_contradiction' ? 'Prediction rejected · worker not invoked' : attempt.decision?.reason === 'contract_rejected' ? 'Contract rejected · worker not invoked' : attempt.prediction_review.status === 'required_agreement' ? 'The rules require agreement' : 'No contradiction found before execution'}</strong>{attempt.prediction_review.proofs.map(proof => <p key={proof.rule}>{proof.explanation}</p>)}<details className="study-details"><summary>Inspect the committed prediction check and execution decision</summary><pre>{JSON.stringify({ review: attempt.prediction_review, decision: attempt.decision }, null, 2)}</pre></details></div>}
        {!!attempt.unverified_execution_artifacts?.length && <p className="study-note">The worker stopped before a measurement was verified. Partial outputs are retained for inspection and excluded from the factual report.</p>}
        {attempt.measurement && <><div className="study-scroll"><table className="study-table source-measurement"><caption>Budget reset: {attempt.measurement.profiles.map(profile => profile.tau).join(' / ')} · warmup excluded</caption><thead><tr><th>History updated</th><th>Misses after warmup</th><th>Gate credits</th></tr></thead><tbody>{attempt.measurement.profiles.map((profile, index) => <tr key={index}><td>{profile.history === 'after_miss' ? 'After misses' : 'After every request'}</td><td><strong>{profile.misses_after_warmup.toLocaleString()}</strong></td><td>{profile.gate_credits}</td></tr>)}</tbody></table></div><p className="study-caption">{attempt.predictions_correct ? 'Both predictions matched.' : 'The measurements differed from one or both predictions.'} {attempt.admission.answers_target ? 'This test answers the finite history question for this seed.' : 'Repeat control only; this does not answer the history question.'}</p><details className="study-details"><summary>Inspect measurement and execution provenance</summary><pre>{JSON.stringify(attempt, null, 2)}</pre></details></>}
      </article>)}
      {record.evidence_report && <div className="study-note"><span className="overline">REPORT DERIVED FROM VERIFIED MEASUREMENTS</span><h3>{record.evidence_report.summary}</h3>{record.provider_mode === 'simulated_provider' && <span className="badge">Simulated planning · actual numerical experiments</span>}<p>{record.evidence_report.measured_tests} history {record.evidence_report.measured_tests === 1 ? 'test' : 'tests'} · {record.evidence_report.control_measurements} repeat {record.evidence_report.control_measurements === 1 ? 'control' : 'controls'}. {record.provider_mode === 'simulated_provider' ? 'Simulated plans; zero live model calls.' : `${record.summary?.inference_requests ?? 0} planning calls · ${record.summary?.usage.total_tokens?.toLocaleString() ?? 'Unreported'} total tokens.`}</p><p>Applies only to measured inputs. Full report disagreement and asymptotic claims remain unresolved.</p><details className="study-details"><summary>Inspect the complete factual report and every citation</summary><pre>{JSON.stringify(record.evidence_report, null, 2)}</pre></details></div>}
      {record.export_available && <a className="button button-primary" href={evidenceHref(`/api/source-investigations/${record.id}/export`)}>Download investigation replay ↓</a>}
    </div>}
  </section>;
}

import { useEffect, useRef, useState } from 'react';
import { isEvidenceBuild, projectFetch } from './access';
import { verifyArchiveBytes } from './archiveIntegrity';
import { canonicalValue, commitPlan, settingsError, valueHash, type ProtocolTemplate, type WorkbenchPlan, type WorkbenchSettings } from './workbenchProtocol';
import './workbench.css';

interface Contract { protocol_template: ProtocolTemplate; presets: { id: string; label: string; settings: WorkbenchSettings }[];
  limits: string[]; runtime: { filename: string; sha256: string; bytes: number; base64: string } }
interface Result extends WorkbenchPlan {
  record_version: number; observations_sha256: string; inference_requests: number; docker_calls: number;
  observations: { input_sha256: string; forecast_sha256: string; gate_difference_observed: boolean; miss_difference_observed: boolean;
    profiles: { history_refresh: string; gate_credits: number; result: { misses: number; hits: number } }[];
    baselines: { policy: string; misses: number }[]; prediction_checks: Record<string, boolean | null> };
}
const pick = (value: boolean | null) => value === null ? 'abstain' : value ? 'differ' : 'agree';
const guess = (value: string) => value === 'abstain' ? null : value === 'differ';
const verdict = (value: boolean | null) => value === null ? 'Abstained · unscored' : value ? 'Matched the measurement' : 'Contradicted by the measurement';
const familyLabel: Record<string, string> = { known_witness: 'Known mechanism witness', uniform: 'Uniform requests', cyclic: 'Cyclic requests', all_fit: 'Everything fits' };

function jsonUrl(value: unknown) { return URL.createObjectURL(new Blob([JSON.stringify(value, null, 2) + '\n'], { type: 'application/json' })); }

export default function ExperimentWorkbench() {
  const [contract, setContract] = useState<Contract | null>(null);
  const [draft, setDraft] = useState<WorkbenchSettings | null>(null);
  const [plan, setPlan] = useState<WorkbenchPlan | null>(null);
  const [planFile, setPlanFile] = useState<{ url: string; hash: string } | null>(null);
  const [runtimeUrl, setRuntimeUrl] = useState('');
  const [records, setRecords] = useState<Result[]>([]);
  const [selected, setSelected] = useState(0);
  const [recordFile, setRecordFile] = useState<{ url: string; hash: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [preparing, setPreparing] = useState(false);
  const [error, setError] = useState('');
  const alive = useRef(true);
  const pending = useRef<AbortController | null>(null);
  const inputsHeading = useRef<HTMLHeadingElement>(null);
  const resultsHeading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    alive.current = true;
    const abort = new AbortController();
    let runtime = '';
    projectFetch('/api/experiment-workbench', { signal: abort.signal }).then(async response => {
      if (!response.ok) throw new Error('The reviewed workbench contract could not be loaded.');
      const data: Contract = await response.json();
      const bytes = Uint8Array.from(atob(data.runtime.base64), char => char.charCodeAt(0));
      await verifyArchiveBytes(bytes, data.runtime);
      if (abort.signal.aborted) return;
      runtime = URL.createObjectURL(new Blob([bytes.buffer], { type: 'application/octet-stream' }));
      setRuntimeUrl(runtime); setContract(data); setDraft({ ...data.presets[0].settings });
    }).catch(cause => { if (!abort.signal.aborted && alive.current) setError(cause instanceof Error ? cause.message : 'The runner failed verification.'); });
    return () => { alive.current = false; abort.abort(); pending.current?.abort(); if (runtime) URL.revokeObjectURL(runtime); };
  }, []);
  useEffect(() => {
    if (!plan) { setPlanFile(null); return; }
    const url = jsonUrl(plan); setPlanFile({ url, hash: plan.protocol_sha256 });
    return () => URL.revokeObjectURL(url);
  }, [plan]);
  const result = records[selected];
  useEffect(() => {
    if (records.length) requestAnimationFrame(() => resultsHeading.current?.focus());
  }, [records.length]);
  useEffect(() => {
    if (!result) { setRecordFile(null); return; }
    const url = jsonUrl(result); setRecordFile({ url, hash: result.protocol_sha256 + ':' + result.observations_sha256 });
    return () => URL.revokeObjectURL(url);
  }, [result]);
  function edit(next: WorkbenchSettings) { setDraft(next); setPlan(null); setError(''); }
  async function commit() {
    if (!draft || !contract || busy || preparing) return;
    setPreparing(true); setError('');
    try { const next = await commitPlan(contract.protocol_template, draft); if (alive.current) setPlan(next); }
    catch (cause) { if (alive.current) setError(cause instanceof Error ? cause.message : 'The plan could not be committed.'); }
    finally { if (alive.current) setPreparing(false); }
  }
  async function run() {
    if (!plan || pending.current || isEvidenceBuild || records.length >= 10) return;
    const committed = plan;
    const abort = new AbortController(); pending.current = abort;
    setBusy(true); setError('');
    try {
      const query = new URLSearchParams({ settings: JSON.stringify(committed.protocol.settings), protocol_sha256: committed.protocol_sha256 });
      const response = await projectFetch(`/api/experiment-workbench/compare?${query}`, { signal: abort.signal });
      if (!response.ok) throw new Error('The local runner refused the settings or committed engine fingerprint. No result was accepted.');
      const next: Result = await response.json();
      if (next.protocol_sha256 !== committed.protocol_sha256 || canonicalValue(next.protocol) !== canonicalValue(committed.protocol)
        || next.observations_sha256 !== await valueHash(next.observations) || next.inference_requests !== 0 || next.docker_calls !== 0) {
        throw new Error('The result does not match the committed plan and response fingerprint.');
      }
      if (alive.current && !abort.signal.aborted) { setRecords(current => [...current, next]); setSelected(records.length); }
    } catch (cause) { if (alive.current && !abort.signal.aborted) setError(cause instanceof Error ? cause.message : 'The comparison stopped. No retry was made.'); }
    finally { pending.current = null; if (alive.current) setBusy(false); }
  }
  if (!contract || !draft) return <p role={error ? 'alert' : 'status'} className={error ? 'error-banner' : 'section-intro'}>{error || 'Checking the bounded experiment contract and portable runner…'}</p>;
  const invalid = settingsError(draft);
  const planUrl = plan && planFile?.hash === plan.protocol_sha256 ? planFile.url : '';
  const recordUrl = result && recordFile?.hash === result.protocol_sha256 + ':' + result.observations_sha256 ? recordFile.url : '';
  const witness = draft.family === 'known_witness';
  const locked = busy || preparing;
  const changed = result && (Object.keys(draft) as (keyof WorkbenchSettings)[]).some(key => draft[key] !== result.protocol.settings[key]);
  const numeric = (key: 'capacity' | 'length' | 'request_seed' | 'algorithm_seed' | 'tau', label: string, min: number, max: number, disabled = false) => <label>{label}<input type="number" min={min} max={max} step={1} value={Number.isFinite(draft[key]) ? draft[key] : ''} disabled={locked || disabled} onChange={event => edit({ ...draft, [key]: event.target.valueAsNumber })} /></label>;
  return <section className="experiment-workbench" aria-labelledby="workbench-title">
    <div className="workbench-intro"><div><span className="overline">DESIGN A BOUNDED EXPERIMENT</span><h2 id="workbench-title">Change the conditions. Keep the evidence.</h2><p>Choose a synthetic request pattern, commit your expectations, then compare the two history rules with the existing exact-layer Python engine.</p></div><span className="badge">Human-designed · zero model calls</span></div>
    <div className="workbench-notice"><strong>Separate from the frozen research benchmark.</strong> These are your synthetic diagnostics. {isEvidenceBuild ? 'This portable browser build prepares plans; use the checked Python runner below to execute them locally.' : 'The local Python calculator runs at most 512 requests with up to 16 cache slots. It writes no workspace files and starts no model, Docker worker or saved investigation.'} Forecasts are generated laboratory advice, not Nemotron predictions.</div>
    <article className="study-panel"><div className="section-title"><h3 ref={inputsHeading} tabIndex={-1}>1. Choose the inputs and expectations</h3><span className="badge">One changed factor: history timing</span></div>
      <div className="workbench-presets" role="group" aria-label="Experiment request families">{contract.presets.map(preset => <button key={preset.id} aria-pressed={draft.family === preset.settings.family} disabled={locked} onClick={() => edit({ ...preset.settings })}>{preset.label}</button>)}</div>
      {witness && <p className="workbench-caption">Previously explored mechanism example: its capacity, requests, fixed forecasts and budget are preserved. You can change the algorithm seed or choose another family to edit the other settings.</p>}
      <div className="workbench-fields">{numeric('capacity', 'Cache slots', 1, 16, witness)}{numeric('length', 'Total requests, including warmup', draft.capacity, 512, witness)}{numeric('request_seed', 'Request-generator seed', 0, 4294967295, draft.family !== 'uniform')}{numeric('algorithm_seed', 'Algorithm seed · shared by both rules', 0, 4294967295)}{numeric('tau', 'Budget reset (τ)', 0, 4, witness)}<label>Synthetic forecasts<select aria-label="Synthetic forecasts" disabled={locked || witness} value={draft.forecast} onChange={event => edit({ ...draft, forecast: event.target.value as WorkbenchSettings['forecast'] })}>{witness ? <option value="fixed_witness">Original witness scores</option> : <><option value="perfect">Perfect next-use forecasts</option><option value="inverted">Inverted next-use forecasts</option></>}</select></label></div>
      <p className="workbench-caption">Uniform requests use k+1 possible pages after k distinct warmup requests. Cyclic requests repeat k+1 pages; the all-fit control repeats only k pages. Perfect advice knows the future; inverted advice reverses its ranking. Neither is a learned model.</p>
      <div className="workbench-predictions">{([['predict_gate_difference', 'Will gate-credit totals differ?'], ['predict_miss_difference', 'Will miss totals differ?']] as const).map(([field, label]) => <label key={field}>{label}<select aria-label={label} disabled={locked} value={pick(draft[field])} onChange={event => edit({ ...draft, [field]: guess(event.target.value) })}><option value="abstain">Abstain · no prediction</option><option value="agree">I predict agreement</option><option value="differ">I predict a difference</option></select></label>)}</div>
      {invalid && <p className="workbench-invalid" role="status">{invalid}</p>}
      <div className="workbench-actions"><button className="button button-primary" disabled={locked || !!invalid} onClick={commit}>{preparing ? 'Committing…' : 'Commit this plan →'}</button>{planUrl && <a className="button button-secondary" href={planUrl} download="counterlab-plan.json">Save committed plan ↓</a>}</div>
      {plan && <div className="workbench-commit"><span className="small-label">COMMITTED SETTINGS AND ENGINE · SHA-256</span><code>{plan.protocol_sha256}</code><p>Edits require a new commitment. This hash binds the plan’s bytes; it is not proof of an external preregistration time.</p>{!isEvidenceBuild && <button className="button button-primary" disabled={busy || records.length >= 10} onClick={run}>{busy ? 'Comparing in local Python…' : 'Run the committed comparison →'}</button>}</div>}
      {error && <p role="alert" className="error-banner">{error}</p>}
      <p className="workbench-caption">Completed comparisons stay in this open view, up to ten. Export results before leaving. No automatic retry; these records never change the frozen evaluation scores.</p>
    </article>
    <article className="study-panel"><div className="section-title"><h3>2. Run or verify it anywhere</h3><span className="badge">Python 3.13 · standard library only</span></div><p className="workbench-caption">Save the committed plan and this checksum-checked runner into a new folder. No account, API key, Docker, network or extra packages are needed. The runner uses the same code fingerprints as the plan.</p><div className="workbench-actions"><a className="button button-secondary" href={runtimeUrl} download="counterlab-experiment.pyz">Save checked Python runner ↓</a></div><code className="workbench-command">python counterlab-experiment.pyz counterlab-plan.json --output counterlab-result.json</code><p className="workbench-caption">To recompute a complete result and reject changed measurements:</p><code className="workbench-command">python counterlab-experiment.pyz counterlab-result.json --verify</code><details className="workbench-details"><summary>Runner fingerprint and experiment limits</summary><code>{contract.runtime.sha256}</code><ul>{contract.limits.map(limit => <li key={limit}>{limit}</li>)}</ul></details></article>
    {result && <article className="study-panel workbench-results"><div className="section-title"><h3 ref={resultsHeading} tabIndex={-1}>3. Inspect a completed comparison</h3><span className="badge">Local Python calculation</span><button className="text-button" onClick={() => inputsHeading.current?.focus()}>Back to draft inputs ↑</button></div><label className="workbench-history">This view’s comparisons<select aria-label="This view’s comparisons" value={selected} onChange={event => setSelected(Number(event.target.value))}>{records.map((record, index) => <option key={index} value={index}>#{index + 1} · {familyLabel[record.protocol.settings.family]} · {record.protocol.settings.capacity} slots · {record.protocol.settings.length} requests · algorithm seed {record.protocol.settings.algorithm_seed}</option>)}</select></label>
      {changed && <p className="workbench-stale"><strong>The draft has changed.</strong> These results belong to the committed settings below. Commit and run the edited plan for a new comparison.</p>}
      <p className="workbench-caption">{familyLabel[result.protocol.settings.family]} · {result.protocol.settings.capacity} slots · {result.protocol.settings.length} requests · {result.protocol.settings.forecast.replaceAll('_', ' ')} · τ {result.protocol.settings.tau}. All counts start from an empty cache and include warmup.</p>
      <div className="study-scroll" tabIndex={0} role="region" aria-label="Completed comparison table"><table className="study-table workbench-table"><thead><tr><th>Rule / baseline</th><th>Cache misses</th><th>Gate credits</th></tr></thead><tbody>{result.observations.profiles.map(profile => <tr key={profile.history_refresh}><th scope="row">{profile.history_refresh === 'after_miss' ? 'History after a miss' : 'History after every request'}</th><td><strong>{profile.result.misses}</strong></td><td>{profile.gate_credits}</td></tr>)}{result.observations.baselines.map(row => <tr key={row.policy}><th scope="row">{row.policy === 'lru' ? 'LRU baseline' : 'Offline optimum · knows future'}</th><td>{row.misses}</td><td>Not applicable</td></tr>)}</tbody></table></div>
      <div className="workbench-outcome"><p>Miss totals: <strong>{result.observations.miss_difference_observed ? 'differ' : 'agree'}</strong>. Gate-credit totals: <strong>{result.observations.gate_difference_observed ? 'differ' : 'agree'}</strong>.</p><p>Your miss prediction: {verdict(result.observations.prediction_checks.predict_miss_difference)}.<br />Your gate prediction: {verdict(result.observations.prediction_checks.predict_gate_difference)}.</p></div>
      <div className="workbench-actions">{recordUrl && <a className="button button-primary" href={recordUrl} download="counterlab-result.json">Save this complete result ↓</a>}</div><details className="workbench-details"><summary>Inspect the exact committed plan and fingerprints</summary><pre tabIndex={0}>{JSON.stringify({ protocol: result.protocol, protocol_sha256: result.protocol_sha256, observations_sha256: result.observations_sha256, input_sha256: result.observations.input_sha256, forecast_sha256: result.observations.forecast_sha256 }, null, 2)}</pre></details><p className="workbench-caption">The complete result includes both raw event streams and synthetic forecasts. The offline optimum is a future-aware bound, not a deployable online competitor. A difference or agreement applies only to these chosen inputs.</p></article>}
  </section>;
}

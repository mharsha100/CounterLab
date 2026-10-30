import { projectFetch, evidenceHref, isEvidenceBuild } from './access';
import { useEffect, useMemo, useState } from 'react';
import './research.css';

interface Profile {
  profile_id: string; profile: { history: string; priority: string; prediction: string };
  misses_cold: number; misses_after_warmup: number; gate_credits: number;
  ratio_cold: number | null; ratio_after_warmup: number | null; trace_sha256: string;
}
interface Observation {
  scenario_id: string; family: string; capacity: number; advice: string; priority_seed: number;
  request_count: number; optimum_cold: number; optimum_after_warmup: number; input_sha256: string; profiles: Profile[];
}
interface Effect {
  factor: string; matched_pairs: number; miss_difference_pairs: number; gate_difference_pairs: number;
  miss_delta_range: number[]; edges: { scenario_id: string; from: string; to: string; miss_delta: number; gate_delta: number }[];
}
interface WitnessEvent { U_before: number; Y_before: number; gate_earned: boolean; decision: string; victim: number | null }
interface Study {
  protocol_sha256: string;
  protocol: { limitations: string[]; held_fixed: string[] };
  summary: { scenario_count: number; profile_runs: number; matched_comparisons: number;
    counting_window_ratio_changes: number; effects: Effect[]; controls: Record<string, boolean> };
  observations: Observation[];
  source_contracts: { differences: { factor: string; support: string; challenge: string; study: string }[];
    sources: { id: string; url: string; sha256: string }[];
    protocol_driver_mismatch: { reported_plan: { requests: number; randomized_repeats_at_least: number };
      executed_driver_default_configuration: { requests: number; randomized_repeats: number }; meaning: string } };
  witness: { scenario_id: string; request_index: number; left: WitnessEvent; right: WitnessEvent };
  execution: { mode: string; completed_at: string; receipts: unknown[]; identical_isolated_replays: boolean };
}
const names: Record<string, string> = {
  history: 'History updates', priority: 'Random priorities', prediction: 'Prediction delivery',
  uniform_k_plus_one: 'Uniform requests', cyclic_k_plus_one: 'Cyclic requests',
  history_witness: 'Timing witness', all_fit: 'Everything fits',
  perfect: 'Perfect advice', time_varying_noise: 'Changing noisy advice', witness_fixed: 'Fixed witness advice',
  after_miss: 'After a miss', after_request: 'Every request', support_entry: 'On entry',
  each_request: 'Every request', stored_at_access: 'At access', fresh_at_decision: 'At decision',
};
const label = (value: string) => names[value] || value.replaceAll('_', ' ');

export default function ResearchStudy() {
  const [study, setStudy] = useState<Study | null>(null);
  const [error, setError] = useState('');
  const [factor, setFactor] = useState('history');
  const [metric, setMetric] = useState<'miss_delta' | 'gate_delta'>('miss_delta');
  const [advice, setAdvice] = useState('all');
  const [selected, setSelected] = useState('history-witness-s0');
  const [window, setWindow] = useState<'cold' | 'warm'>('cold');
  useEffect(() => {
    const controller = new AbortController();
    projectFetch('/api/research-study', { signal: controller.signal }).then(async response => {
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || 'The study could not be verified.');
      setStudy(body as Study);
    }).catch(cause => { if (cause.name !== 'AbortError') setError(cause.message); });
    return () => controller.abort();
  }, []);
  const visible = useMemo(() => study?.observations.filter(row => advice === 'all' || row.advice === advice) || [], [study, advice]);
  if (error) return <div className="error-banner" role="alert"><strong>Research study unavailable.</strong> {error}</div>;
  if (!study) return <div className="loading-card" role="status"><span className="spinner" /> {isEvidenceBuild ? 'Checking recorded evidence…' : 'Verifying the frozen study and replaying its measurements…'}</div>;
  const effect = study.summary.effects.find(item => item.factor === factor)!;
  const visibleIds = new Set(visible.map(item => item.scenario_id));
  const deltas = effect.edges.filter(edge => visibleIds.has(edge.scenario_id)).map(edge => edge[metric]);
  const range = [Math.min(...deltas), Math.max(...deltas)].map(value => value > 0 ? `+${value}` : String(value));
  const row = study.observations.find(item => item.scenario_id === selected)!;
  const mismatch = study.source_contracts.protocol_driver_mismatch;
  return <section className="research-view">
    <div className="section-title"><div><span className="overline">SOURCE CONTRACTS → CONTROLLED INTERVENTIONS</span><h2>Which settings change the result?</h2></div><span className="badge badge-green">Numerical replay verified</span></div>
    <p className="section-intro">A frozen finite study of {study.summary.scenario_count} scenarios and all eight combinations of three settings. These are controlled profiles in our own runner. Full published implementation parity and the research disagreement remain unresolved.</p>
    <div className="study-stats"><div><strong>{study.summary.profile_runs}</strong><span>profile runs, each replayed twice in isolation</span></div><div><strong>{study.summary.matched_comparisons}</strong><span>pairs changing exactly one behavior setting</span></div><div><strong>0</strong><span>model requests · this study is deterministic</span></div></div>

    <article className="study-panel"><div className="section-title"><h3>Check comparability first.</h3><span className="badge">Pinned source audit</span></div>
      <div className="study-scroll" tabIndex={0} role="region" aria-label="Source settings comparison table"><table className="study-table"><thead><tr><th>Setting</th><th>Supporting implementation</th><th>Challenging implementation</th><th>Our controlled test</th></tr></thead><tbody>{study.source_contracts.differences.map(item => <tr key={item.factor}><th scope="row">{item.factor}</th><td>{item.support}</td><td>{item.challenge}</td><td>{item.study}</td></tr>)}</tbody></table></div>
      <div className="study-note"><strong>The plan and driver defaults also differ.</strong><p>The supporting protocol specifies {mismatch.reported_plan.requests.toLocaleString()} requests and at least {mismatch.reported_plan.randomized_repeats_at_least} repeats. Its driver defaults specify {mismatch.executed_driver_default_configuration.requests.toLocaleString()} and {mismatch.executed_driver_default_configuration.randomized_repeats}. {mismatch.meaning}</p></div>
      <details className="study-details"><summary>Inspect the six pinned sources and hashes</summary>{study.source_contracts.sources.map(source => <div className="study-source" key={source.id}><a href={source.url} target="_blank" rel="noreferrer">{label(source.id)} ↗</a><code>{source.sha256}</code></div>)}</details>
    </article>

    <article className="study-panel"><div className="section-title"><div><span className="overline">CONDITIONAL MAP</span><h3>A difference depends on the inputs.</h3></div></div>
      <div className="study-controls"><div className="study-tabs" role="group" aria-label="Behavior setting">{study.summary.effects.map(item => <button key={item.factor} aria-pressed={factor === item.factor} onClick={() => setFactor(item.factor)}>{label(item.factor)}</button>)}</div><label>Compare<select value={metric} onChange={event => setMetric(event.target.value as typeof metric)}><option value="miss_delta">Miss counts</option><option value="gate_delta">Gate credits</option></select></label><label>Advice<select value={advice} onChange={event => setAdvice(event.target.value)}><option value="all">All conditions</option>{['perfect', 'time_varying_noise', 'witness_fixed'].map(value => <option key={value} value={value}>{label(value)}</option>)}</select></label></div>
      <p className="study-caption">Each cell shows pairs with a measured difference / all matched pairs. The other two settings stay fixed within each pair. A zero is a measured null result.</p>
      <div className="study-scroll" tabIndex={0} role="region" aria-label="Conditional difference map"><table className="study-table study-map"><thead><tr><th>Request family / cache slots</th>{[4, 8, 16, 32].map(capacity => <th key={capacity}>{capacity}</th>)}</tr></thead><tbody>{['uniform_k_plus_one', 'cyclic_k_plus_one', 'history_witness', 'all_fit'].map(family => <tr key={family}><th scope="row">{label(family)}</th>{[4, 8, 16, 32].map(capacity => {
        const ids = new Set(visible.filter(item => item.family === family && item.capacity === capacity).map(item => item.scenario_id));
        const pairs = effect.edges.filter(edge => ids.has(edge.scenario_id));
        const changes = pairs.filter(edge => edge[metric] !== 0).length;
        return <td key={capacity} className={changes ? 'study-cell-diff' : ''}>{pairs.length ? <button aria-label={`${label(family)}, ${capacity} slots: ${changes} of ${pairs.length} pairs differ. Inspect a scenario.`} onClick={() => setSelected(pairs.find(edge => edge[metric] !== 0)?.scenario_id || pairs[0].scenario_id)}><strong>{changes}</strong> / {pairs.length}</button> : <span className="muted">—</span>}</td>;
      })}</tr>)}</tbody></table></div>
      <p className="study-caption">For the selected conditions, changing {label(factor).toLowerCase()} shifts {metric === 'miss_delta' ? 'miss counts' : 'gate credits'} by <strong>{range[0]} to {range[1]}</strong>. The difference is level 1 minus level 0: {factor === 'history' ? 'every request minus after a miss' : factor === 'priority' ? 'every request minus support entry' : 'at decision minus at access'}. Both signs mean the direction varies across inputs.</p>
      <p className="study-caption">Seeds and factorial arms share inputs and are correlated. Counts describe this development suite; they are not independent scientific discoveries or statistical confidence estimates.</p>
    </article>

    <article className="study-panel" id="study-scenario"><div className="section-title"><h3>Inspect every arm.</h3><span className="badge">No outcome hidden</span></div>
      <div className="study-controls"><label className="study-scenario-select">Scenario<select value={selected} onChange={event => setSelected(event.target.value)}>{study.observations.map(item => <option key={item.scenario_id} value={item.scenario_id}>{label(item.family)} · k={item.capacity} · {label(item.advice)} · seed {item.priority_seed}</option>)}</select></label><label>Count misses<select value={window} onChange={event => setWindow(event.target.value as typeof window)}><option value="cold">From empty cache</option><option value="warm">After common warmup</option></select></label></div>
      <p className="study-caption">{row.request_count} requests · {row.capacity} slots · offline optimum: <strong>{window === 'cold' ? row.optimum_cold : row.optimum_after_warmup} misses</strong>. The window applies equally to the algorithm and its baseline.</p>
      <div className="study-scroll" tabIndex={0} role="region" aria-label="All study arms table"><table className="study-table"><thead><tr><th>Arm</th><th>History</th><th>Priorities</th><th>Predictions</th><th>Credits</th><th>Misses</th><th>Ratio to optimum</th></tr></thead><tbody>{row.profiles.map(profile => { const ratio = window === 'cold' ? profile.ratio_cold : profile.ratio_after_warmup; return <tr key={profile.profile_id}><th scope="row"><code>{profile.profile_id}</code></th><td>{label(profile.profile.history)}</td><td>{label(profile.profile.priority)}</td><td>{label(profile.profile.prediction)}</td><td>{profile.gate_credits}</td><td><strong>{window === 'cold' ? profile.misses_cold : profile.misses_after_warmup}</strong></td><td>{ratio == null ? 'Undefined (0 / 0)' : ratio.toFixed(3)}</td></tr>; })}</tbody></table></div>
      <details className="study-details"><summary>Inspect this scenario’s input and trace fingerprints</summary><pre tabIndex={0}>{JSON.stringify({ input_sha256: row.input_sha256, profiles: row.profiles.map(profile => ({ arm: profile.profile_id, trace_sha256: profile.trace_sha256 })) }, null, 2)}</pre></details>
    </article>

    <article className="study-panel"><div className="section-title"><div><span className="overline">FIRST DIFFERING GATE DECISION</span><h3>See the state that changes the decision.</h3></div><span className="badge">Timing witness · seed 0</span></div><p className="study-caption">Request {study.witness.request_index + 1} of the previously explored witness. Only history timing changes between these arms. This is development reuse.</p>
      <div className="study-witness">{[study.witness.left, study.witness.right].map((event, index) => <div key={index}><span className="small-label">{index === 0 ? 'AFTER A MISS' : 'AFTER EVERY REQUEST'}</span><h3>{event.gate_earned ? 'One credit earned.' : 'No credit earned.'}</h3><p>U = {event.U_before}, saved Y = {event.Y_before}</p><code>{event.U_before} ≤ (({event.Y_before} + 2) / e) − 2</code><p>Threshold: {((event.Y_before + 2) / Math.E - 2).toFixed(3)} · {event.gate_earned ? 'passes' : 'fails'}</p></div>)}</div>
    </article>

    <article className="study-panel"><div className="section-title"><h3>Controls, provenance and limits.</h3><span className="badge badge-green">{Object.values(study.summary.controls).filter(Boolean).length} / {Object.keys(study.summary.controls).length} controls passed</span></div>
      <ul className="study-checks">{Object.entries(study.summary.controls).map(([name, passed]) => <li key={name}><span>{passed ? '✓' : '!'}</span>{label(name)}</li>)}</ul>
      <p className="study-caption">Changing the counting window changes {study.summary.counting_window_ratio_changes} finite ratios without changing any eviction. Finite growth over a few cache sizes cannot establish or refute an asymptotic bound.</p>
      <details className="study-details"><summary>Read all limitations and fixed conditions</summary><ul>{study.protocol.limitations.map(limit => <li key={limit}>{limit}</li>)}</ul><h4>Held fixed</h4><ul>{study.protocol.held_fixed.map(item => <li key={item}>{item}</li>)}</ul></details>
      <div className="study-fingerprint"><span className="small-label">COMMITTED BEFORE EXECUTION · SHA-256</span><code>{study.protocol_sha256}</code></div>
      <div className="export-panel"><div><h3>Replay all {study.summary.profile_runs} profile runs.</h3><p>Own numerical code, frozen protocol, all observations and source references. No external algorithm code or API key. Python replay uses no credits.</p></div><a className="button button-primary" href={evidenceHref("/api/research-study/export")}>Download study & replay ↓</a></div>
    </article>
  </section>;
}

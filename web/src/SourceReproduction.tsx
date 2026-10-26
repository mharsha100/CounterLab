import { projectFetch, evidenceHref, isEvidenceBuild } from './access';
import { useEffect, useState } from 'react';
import './research.css';
import './source.css';

interface Reproduction {
  protocol_sha256: string;
  protocol: { rules: Record<string, string>; limits: string[] };
  source_metadata: { source_url: string; source_sha256: string };
  summary: { status: string; capacity: number; horizon: number; randomized_repeats: number;
    published_rows_matched: number; published_rows_compared: number; profile_runs: number;
    miss_difference_pairs: number; delta_range: number[];
    rows: { alg: string; our_optimum: number; reported_optimum: number; our_ratio_mean: number;
      reported_ratio_mean: number; our_ratio_std: number; reported_ratio_std: number;
      mean_difference: number; std_difference: number; matches: boolean; individual_costs: number[]; repeats: number }[];
    history_intervention: { seed: number; source_misses: number; after_miss_misses: number; miss_delta: number;
      source_gate_credits: number; after_miss_gate_credits: number; source_trace_sha256: string; after_miss_trace_sha256: string }[] };
  observations: { seed: number; input_sha256: string; prediction_sha256: string; warmup_length: number; initial_pages: number[] }[];
  execution: { receipts: unknown[]; identical_isolated_replays: boolean; host_replay_verified: boolean };
  validation: { profiles_checked: number; post_warmup_events_checked: number; original_prefix_checks: number };
  verification: { note: string; published_data_verified: boolean };
}
const names: Record<string, string> = { 'OnOPT-OM': 'OnOPT-OM · budget reset 0', 'RPB-OM(tau=1)': 'RPB-OM · budget reset 1', LRU: 'Source LRU control' };
const signed = (value: number) => value > 0 ? `+${value}` : String(value);

export default function SourceReproduction({ onInvestigate }: { onInvestigate?: () => void }) {
  const [data, setData] = useState<Reproduction | null>(null);
  const [error, setError] = useState('');
  const [seed, setSeed] = useState(900);
  useEffect(() => {
    const controller = new AbortController();
    projectFetch('/api/source-reproduction', { signal: controller.signal }).then(async response => {
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || 'The source reconstruction could not be verified.');
      setData(body);
    }).catch(cause => { if (cause.name !== 'AbortError') setError(cause.message); });
    return () => controller.abort();
  }, []);
  if (error) return <div className="error-banner" role="alert"><strong>Source reconstruction unavailable.</strong> {error}</div>;
  if (!data) return <div className="loading-card" role="status"><span className="spinner" /> Checking the frozen source record and selected aggregates…</div>;
  const summary = data.summary;
  const selected = summary.history_intervention.find(row => row.seed === seed)!;
  const observation = data.observations.find(row => row.seed === seed)!;
  const matched = summary.published_rows_matched === summary.published_rows_compared;
  return <section className="research-view source-reproduction">
    <div className="section-title"><div><span className="overline">ONE SOURCE REGIME · ORIGINAL TRACE LENGTH</span><h2>Reconstruct first. Then change one rule.</h2></div><span className={`badge ${matched ? 'badge-green' : 'badge-amber'}`}>{summary.published_rows_matched} / {summary.published_rows_compared} selected reference rows matched</span></div>
    <p className="section-intro">A reconstruction of three selected rows from a supporting independent reproduction’s E4 experiment: uniform requests, {summary.capacity} cache slots and inverted next-use predictions. Reported values stay separate from our measurements. This is one finite source slice.</p>
    <div className="study-stats"><div><strong>{summary.horizon.toLocaleString()}</strong><span>original requests · no injected warmup prefix</span></div><div><strong>{summary.randomized_repeats}</strong><span>algorithm seeds on the same input trace</span></div><div><strong>{summary.profile_runs}</strong><span>profile runs · each replayed twice in isolation and on the host</span></div></div>
    <article className="study-panel"><div className="section-title"><h3>Do our numbers match the source?</h3><a className="source-link" href={data.source_metadata.source_url} target="_blank" rel="noreferrer">Inspect the pinned numeric artifact ↗</a></div>
      <p className="study-caption">Cost ratio = misses after warmup / offline-optimal misses after the same warmup. Both denominators are {summary.rows[0].our_optimum.toLocaleString()}. Agreement requires exact OPT and an absolute tolerance of 10⁻¹² for both the mean ratio and its sample standard deviation.</p>
      <div className="study-scroll"><table className="study-table source-comparison"><thead><tr><th>Source algorithm</th><th>Reported ratio</th><th>Our ratio</th><th>Mean residual</th><th>Match</th></tr></thead><tbody>{summary.rows.map(row => <tr key={row.alg}><th scope="row">{names[row.alg] || row.alg}<span className="source-row-note">{row.repeats} {row.repeats === 1 ? 'run' : 'seed repeats'}</span></th><td>{row.reported_ratio_mean.toFixed(6)}</td><td><strong>{row.our_ratio_mean.toFixed(6)}</strong></td><td>{row.mean_difference === 0 ? '0' : row.mean_difference.toExponential(2)}</td><td>{row.matches ? '✓ Within tolerance' : 'Review mismatch'}</td></tr>)}</tbody></table></div>
      <details className="study-details"><summary>Inspect standard deviations and every individual cost</summary><pre>{JSON.stringify(summary.rows, null, 2)}</pre></details>
      <div className="study-note"><strong>A precise source contract includes its initialization choices.</strong><p>The source collects the first 16 distinct pages, then resets layers and LRU order to that first-distinct order. We reproduce that reset, its original forecast formula, the exact random-number schedule and the post-warmup counting window. This reset differs from processing the repeated warmup accesses through the canonical cold-start state.</p></div>
    </article>
    <article className="study-panel"><div className="section-title"><div><span className="overline">MATCHED HISTORY INTERVENTION · BUDGET RESET 1</span><h3>{summary.miss_difference_pairs ? 'Does timing change this source regime?' : 'Miss counts agree in this source regime.'}</h3></div><span className="badge">Every seed retained</span></div>
      <p className="study-caption">Change history updates from every request to after a miss. Keep requests, stored forecasts, priorities, budget reset, initialization and cost window fixed. Miss counts differ in <strong>{summary.miss_difference_pairs} / 10</strong> paired seeds; after-miss minus source ranges from <strong>{signed(summary.delta_range[0])} to {signed(summary.delta_range[1])}</strong>. A zero remains a measured null.</p>
      <div className="study-scroll"><table className="study-table"><thead><tr><th>Algorithm seed</th><th>Source misses</th><th>After-miss misses</th><th>Difference</th><th>Source credits</th><th>After-miss credits</th></tr></thead><tbody>{summary.history_intervention.map(row => <tr key={row.seed} className={row.seed === seed ? 'source-selected-row' : ''}><th scope="row"><button className="text-button" aria-label={`Inspect seed ${row.seed}`} onClick={() => setSeed(row.seed)}>{row.seed}</button></th><td>{row.source_misses.toLocaleString()}</td><td>{row.after_miss_misses.toLocaleString()}</td><td><strong>{signed(row.miss_delta)}</strong></td><td>{row.source_gate_credits}</td><td>{row.after_miss_gate_credits}</td></tr>)}</tbody></table></div>
      <p className="study-caption">The source’s after-every-request history earns zero gate credits, as its state equation predicts. The ten seeds share a request trace and are correlated. These results do not establish a general performance ranking or explain the entire published disagreement.</p>
      <details className="study-details"><summary>Inspect selected seed {seed}, inputs and trace fingerprints</summary><pre>{JSON.stringify({ ...observation, intervention: selected }, null, 2)}</pre></details>
    </article>
    {onInvestigate && <div className="export-panel"><div><h3>Investigate this source regime.</h3><p>Let Nemotron commit predictions and choose a bounded source test. New planning calls require separate credit approval.</p></div><button className="button button-primary" onClick={onInvestigate}>Open source investigator →</button></div>}
    <article className="study-panel"><div className="section-title"><h3>What was checked, and what remains open?</h3><span className="badge badge-green">Reconstruction: zero inference requests</span></div>
      <ul className="study-checks"><li><span>✓</span>Two isolated replays and a host replay for each seed; all event fingerprints agree.</li><li><span>✓</span>{data.validation.profiles_checked} independent work-function checks and {data.validation.post_warmup_events_checked.toLocaleString()} events, including {data.validation.original_prefix_checks} original-input prefix checks.</li><li><span>{data.verification.published_data_verified ? '✓' : 'i'}</span>{data.verification.published_data_verified ? `Full upstream numeric file hash-verified ${isEvidenceBuild ? 'at packaging' : 'in this environment'}.` : 'Full upstream file not verified here; selected comparison values are checked against the frozen local record.'}</li><li><span>✓</span>Source-code, protocol, receipts and summary verified before display.</li></ul>
      <p className="study-caption">{data.verification.note}</p>
      <div className="study-note"><strong>This is a selected supporting-report reconstruction.</strong><p>The original paper’s official implementation, forgiveness behavior, real traces, other source regimes and the challenging lazy-adversary experiment have not been reproduced here. No asymptotic theorem has been proved or refuted. This run was selected and executed by the developer; it is not evidence of autonomous model experiment selection.</p></div>
      <details className="study-details"><summary>Inspect the frozen operational rules and all limits</summary><dl className="source-rule-list">{Object.entries(data.protocol.rules).map(([name, value]) => <div key={name}><dt>{name.replaceAll('_',' ')}</dt><dd>{value}</dd></div>)}</dl><ul>{data.protocol.limits.map(limit => <li key={limit}>{limit}</li>)}</ul></details>
      <div className="study-fingerprint"><span className="small-label">FROZEN BEFORE FULL EXECUTION · SHA-256</span><code>{data.protocol_sha256}</code></div>
      <div className="export-panel"><div><h3>Replay the full selected slice.</h3><p>Our code, frozen settings, three attributed reference rows and all seeds. The full upstream file is not bundled. Before the full replay, explicitly run python fetch_reference.py --download to fetch and hash-check that file. Replay then runs offline with standard-library Python and uses no credits.</p></div><a className="button button-primary" href={evidenceHref("/api/source-reproduction/export")}>Download source replay ↓</a></div>
    </article>
  </section>;
}

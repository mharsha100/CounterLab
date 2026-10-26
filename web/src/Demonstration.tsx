import { projectFetch, evidenceHref, isEvidenceBuild } from './access';
import { useEffect, useRef, useState } from 'react';
import PredictionReview, { policyLabels, type Audit } from './PredictionReview';
import TraceExplorer from './TraceExplorer';
import './research.css';
import './demonstration.css';

interface Plan { test_id: string; hypothesis: string; predict_gate_difference: boolean; predict_miss_difference: boolean }
interface Scene { task_id: string; capacity: number; horizon: number; question: string; run: {
  inference_requests: number; attempts: { plan: Plan; measurement: { evidence_id: string; seed: number; profiles: { history: string; misses_after_warmup: number; gate_credits: number }[] } | null }[];
  evidence_report: { summary: string; outcome: string };
} }
interface Data { mode: string; provider: string; model: string; scenes: Scene[]; batch_calls: number; batch_usage: { total_tokens: number };
  policies: { policy: string; differences_found: number; difference_tasks: number; correct_predictions: number; predictions_checked: number; inference_requests: number }[];
  oracle: { profiles_checked: number; post_warmup_events_checked: number }; prediction_review: Audit;
  task_protocol_sha256: string; execution_protocol_sha256: string; limits: string[];
}
const steps = ['An experiment', 'A failed prediction', 'A fair comparison', 'Replay it yourself'];
const prediction = (different: boolean) => different ? 'Different' : 'The same';

function SceneEvidence({ scene }: { scene: Scene }) {
  const attempt = scene.run.attempts.find(row => row.measurement)!;
  const evidence = attempt.measurement!;
  return <>
    <div className="demo-facts"><span>{scene.capacity} cache slots</span><span>{scene.horizon.toLocaleString()} requests</span><span>Seed {evidence.seed}</span><span>History timing changes</span></div>
    <div className="demo-flow"><div><span className="overline">01 · SAVED MODEL PLAN</span><h3>{attempt.plan.test_id.replaceAll('_', ' ')}</h3><p>Gate credits: <strong>{prediction(attempt.plan.predict_gate_difference)}</strong><br />Miss counts: <strong>{prediction(attempt.plan.predict_miss_difference)}</strong></p><details><summary>Read the unverified hypothesis</summary><p>{attempt.plan.hypothesis}</p></details></div><div><span className="overline">02 · VERIFIED MEASUREMENTS</span><table className="demo-measurements"><caption>Counts after warmup</caption><thead><tr><th>History updated</th><th>Misses</th><th>Credits</th></tr></thead><tbody>{evidence.profiles.map((profile, index) => <tr key={index}><th scope="row">{profile.history === 'after_request' ? 'Every request' : 'After misses'}</th><td>{profile.misses_after_warmup}</td><td>{profile.gate_credits}</td></tr>)}</tbody></table></div></div>
    <div className="demo-finding"><span className="overline">03 · FACTUAL REPORT FROM REPLAYED COUNTS</span><p>{scene.run.evidence_report.summary}</p><details><summary>Inspect the evidence fingerprint</summary><code>{evidence.evidence_id}</code></details></div>
  </>;
}

export default function Demonstration({ onEvaluation }: { onEvaluation: () => void }) {
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState('');
  const [step, setStep] = useState(0);
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    const controller = new AbortController();
    projectFetch('/api/demonstration', { signal: controller.signal }).then(async response => {
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || 'The recorded evidence could not be verified.');
      setData(body);
    }).catch(cause => { if (cause.name !== 'AbortError') setError(cause.message); });
    return () => controller.abort();
  }, []);
  function go(next: number) { setStep(next); requestAnimationFrame(() => heading.current?.focus()); }
  if (error) return <p className="error-banner" role="alert">{error}</p>;
  if (!data) return <p className="section-intro" role="status">{isEvidenceBuild ? 'Checking the packaged demonstration evidence…' : 'Replaying and verifying the recorded demonstration evidence…'}</p>;
  const scene = data.scenes[step === 1 ? 1 : 0];
  return <section className="research-view demo-view">
    <div className="demo-intro"><div><span className="overline">A GUIDED EVIDENCE TOUR · ABOUT 3 MINUTES</span><h2>Can we trust the experiment?</h2><p>CounterLab lets an AI choose a test, then checks what the evidence can actually support.</p></div><span className="badge">Recorded real Nemotron responses</span></div>
    <div className="demo-recording"><strong>Recorded inspection · no new inference.</strong> These are saved {data.model.replace('nvidia/', '')} responses through {data.provider}. Model-selected tests replayed premeasured outcomes from isolated experiments. This tour starts no model or worker calls.</div>
    <nav className="demo-steps" aria-label="Demonstration steps">{steps.map((label, index) => <button key={label} aria-pressed={step === index} onClick={() => go(index)}><span>{String(index + 1).padStart(2, '0')}</span>{label}</button>)}</nav>
    <article className="study-panel demo-scene">
      <span className="overline">{String(step + 1).padStart(2, '0')} / 04</span>
      <h2 ref={heading} tabIndex={-1}>{step === 0 ? 'One changed rule. A measured difference.' : step === 1 ? 'A confident prediction can be impossible.' : step === 2 ? 'Finding a difference is only one score.' : 'The evidence leaves the app with you.'}</h2>
      <p className="demo-lede">{step === 0 ? 'A caching algorithm decides which page to evict. Here, only the timing of its history update changes; requests, forecasts, random tape and the other settings stay fixed.' : step === 1 ? 'On this smaller cache, the model predicted that both counts would differ. They agreed. A necessary-condition check can also explain why a difference was impossible.' : step === 2 ? 'Every scheduled run stays in the comparison, including controls, rejected tests and responses that exhausted their output limit.' : 'Download the frozen inputs, saved model responses, numerical results and verification code. Recompute them with Python, without a key, Docker, network access or credits.'}</p>
      {step < 2 && <SceneEvidence scene={scene} />}
      {step === 0 && <TraceExplorer />}
      {step === 1 && <div className="demo-proof"><strong>Why the prediction contradicts the rules</strong><p>A support miss requires U≥1, and saved history Y≤k. With {scene.capacity} slots, (Y+2)/e−2 is below 1, so the gate cannot activate under either timing rule. The identical eviction rules then give identical miss counts.</p><p>This is a later review. The batch executed these tests and its original scores remain unchanged.</p></div>}
      {step === 2 && <><div className="study-scroll"><table className="study-table"><thead><tr><th>Policy</th><th>Finite differences found / available</th><th>Both predictions correct</th><th>Model calls</th></tr></thead><tbody>{data.policies.map(row => <tr key={row.policy}><th scope="row">{policyLabels[row.policy]}</th><td>{row.differences_found} / {row.difference_tasks}</td><td>{row.correct_predictions} / {row.predictions_checked}</td><td>{row.inference_requests}</td></tr>)}</tbody></table></div><div className="demo-proof"><strong>No advantage over the contract heuristic is established.</strong><p>The adaptive model found both available finite differences, as did the simple baselines. Its predictions remain unreliable. Factual reporting is a shared backend check, not a model reasoning score.</p></div><p className="study-caption">{data.batch_calls} model calls · {data.batch_usage.total_tokens.toLocaleString()} reported tokens · two truncated fixed-policy responses retained · no retries. One repeat in one known generator cannot establish a general ranking.</p><button className="button button-secondary" onClick={onEvaluation}>Inspect all tasks and policies →</button></>}
      {step === 3 && <><div className="study-stats"><div><strong>{data.oracle.profiles_checked}</strong><span>distinct profiles independently checked</span></div><div><strong>{data.oracle.post_warmup_events_checked.toLocaleString()}</strong><span>post-warmup events checked</span></div><div><strong>0</strong><span>model calls needed for replay</span></div></div><p className="study-caption">The independent validator enumerates reachable cache configurations and minimum prefix costs. Hashes check consistency within this package; they do not establish independent authorship.</p><div className="demo-downloads"><a className="button button-primary" href={evidenceHref("/api/source-evaluation/export")}>Download full evaluation replay ↓</a><a className="button button-secondary" href={evidenceHref("/api/prediction-review/export")}>Download later prediction review ↓</a></div><details className="study-details"><summary>Inspect frozen protocol fingerprints</summary><p>Tasks</p><code>{data.task_protocol_sha256}</code><p>Execution and scoring</p><code>{data.execution_protocol_sha256}</code></details><div className="demo-proof"><strong>What remains open</strong><ul>{data.limits.map(limit => <li key={limit}>{limit}</li>)}</ul></div></>}
      <div className="demo-controls"><button className="button button-secondary" disabled={step === 0} onClick={() => go(step - 1)}>← Previous</button><span>Step {step + 1} of {steps.length}</span><button className="button button-primary" onClick={() => go(step === 3 ? 0 : step + 1)}>{step === 3 ? 'Start again ↺' : 'Next →'}</button></div>
    </article>
    {step === 1 && <PredictionReview supplied={data.prediction_review} taskId={scene.task_id} />}
  </section>;
}

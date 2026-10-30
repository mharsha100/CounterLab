import { projectFetch, evidenceHref, isEvidenceBuild } from './access';
import { useEffect, useRef, useState } from 'react';
import PredictionReview, { policyLabels, type Audit } from './PredictionReview';
import TraceExplorer from './TraceExplorer';
import './research.css';
import './demonstration.css';

interface Plan { test_id: string; hypothesis: string; predict_gate_difference: boolean; predict_miss_difference: boolean }
interface Scene { task_id: string; capacity: number; horizon: number; question: string; run: {
  inference_requests: number; attempts: { plan: Plan; admission?: { reason: string; explanation: string }; measurement: { evidence_id: string; seed: number; profiles: { history: string; misses_after_warmup: number; gate_credits: number }[] } | null }[];
  evidence_report: { summary: string; outcome: string };
} }
interface Data { mode: string; provider: string; model: string; scenes: Scene[]; batch_calls: number; batch_usage: { total_tokens: number };
  policies: { policy: string; differences_found: number; difference_tasks: number; correct_predictions: number; predictions_checked: number; inference_requests: number }[];
  oracle: { profiles_checked: number; post_warmup_events_checked: number }; prediction_review: Audit;
  task_protocol_sha256: string; execution_protocol_sha256: string; limits: string[];
}
const steps = ['An experiment', 'A failed prediction', 'A fair comparison', 'Replay it yourself'];
const prediction = (different: boolean) => different ? 'Different' : 'The same';
const testName = (id: string) => id.replace(/^test_(\d+)$/, 'Test $1').replaceAll('_', ' ');
const testPurpose = (reason?: string) => reason ? `${reason.charAt(0).toUpperCase()}${reason.slice(1).replaceAll('_', ' ')}` : '';

function outcome(scene: Scene) {
  const attempt = scene.run.attempts.find(row => row.measurement)!;
  const evidence = attempt.measurement!;
  const [left, right] = evidence.profiles;
  const gate = left.gate_credits !== right.gate_credits;
  const misses = left.misses_after_warmup !== right.misses_after_warmup;
  return { attempt, evidence, gate, misses, gateCorrect: attempt.plan.predict_gate_difference === gate,
    missesCorrect: attempt.plan.predict_miss_difference === misses };
}

function Verdict({ label, predicted, measured }: { label: string; predicted: boolean; measured: boolean }) {
  const correct = predicted === measured;
  return <li className={correct ? 'verdict-correct' : 'verdict-wrong'}><span className="verdict-metric">{label}</span>
    <span>Predicted <strong>{prediction(predicted)}</strong></span><span>Measured <strong>{prediction(measured)}</strong></span>
    <span className="verdict-mark">{correct ? '✓ Prediction held' : '✗ Prediction failed'}</span></li>;
}

function SceneEvidence({ scene }: { scene: Scene }) {
  const { attempt, evidence, gate, misses } = outcome(scene);
  return <>
    <div className="demo-facts"><span>{scene.capacity} cache slots</span><span>{scene.horizon.toLocaleString()} requests</span><span>Seed {evidence.seed}</span><span>History timing changes</span></div>
    <div className="demo-flow"><div><span className="overline">01 · NEMOTRON COMMITTED THIS BEFORE ANYTHING RAN</span><h3>{testName(attempt.plan.test_id)}{attempt.admission ? ` · ${testPurpose(attempt.admission.reason)}` : ''}</h3>{attempt.admission?.explanation && <p className="demo-test-note">{attempt.admission.explanation}</p>}<p>Gate credits: <strong>{prediction(attempt.plan.predict_gate_difference)}</strong><br />Miss counts: <strong>{prediction(attempt.plan.predict_miss_difference)}</strong></p><details><summary>Read the model’s unverified hypothesis</summary><p>{attempt.plan.hypothesis}</p></details></div><div><span className="overline">02 · ISOLATED WORKERS MEASURED IT TWICE</span><table className="demo-measurements"><caption>Counts after warmup</caption><thead><tr><th scope="col">History updated</th><th scope="col">Misses</th><th scope="col">Credits</th></tr></thead><tbody>{evidence.profiles.map((profile, index) => <tr key={index}><th scope="row">{profile.history === 'after_request' ? 'Every request' : 'After misses'}</th><td>{profile.misses_after_warmup}</td><td>{profile.gate_credits}</td></tr>)}</tbody></table></div></div>
    <ul className="demo-verdicts" aria-label="Prediction compared with measurement"><Verdict label="Gate credits" predicted={attempt.plan.predict_gate_difference} measured={gate} /><Verdict label="Miss counts" predicted={attempt.plan.predict_miss_difference} measured={misses} /></ul>
    <div className="demo-finding"><span className="overline">03 · FINDING WRITTEN BY CODE FROM THE REPLAYED COUNTS — NOT BY THE MODEL</span><p>{scene.run.evidence_report.summary}</p><details><summary>Inspect the evidence fingerprint</summary><code>{evidence.evidence_id}</code></details></div>
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
  const headline = outcome(data.scenes[0]);
  return <section className="research-view demo-view">
    <div className="demo-hero">
      <div className="demo-hero-copy"><span className="overline">THE 30-SECOND VERSION</span><h2>Nemotron proposes the experiment. CounterLab makes it prove it.</h2><p>When two implementations of the same algorithm disagree, an AI explanation is cheap. CounterLab has NVIDIA Nemotron commit a test and a prediction <em>before</em> anything runs, measures the test in isolated workers and writes the finding only from those measurements, so anyone can replay it without trusting the AI.</p></div>
      <ol className="demo-pipeline" aria-label="Who does what in an investigation">
        <li className="pipeline-ai"><span className="pipeline-actor">{data.model.replace('nvidia/', 'NVIDIA ')} · {data.provider}</span><strong>Chooses a test and commits predictions</strong><span>Schema-constrained JSON · at most two planning calls</span></li>
        <li><span className="pipeline-actor">Deterministic guard</span><strong>Rejects non-comparable or impossible plans</strong><span>Before any worker starts</span></li>
        <li><span className="pipeline-actor">Isolated workers</span><strong>Measure each admitted test twice</strong><span>No network · host replay must match</span></li>
        <li><span className="pipeline-actor">Evidence reporter</span><strong>Writes the finding from measurements</strong><span>No model-generated numbers · offline replay</span></li>
      </ol>
      <div className="demo-headline" role="note"><span className="overline">RECORDED NEMOTRON RUN</span><p>Nemotron predicted gate credits would be <strong>{prediction(headline.attempt.plan.predict_gate_difference).toLowerCase()}</strong> and misses <strong>{prediction(headline.attempt.plan.predict_miss_difference).toLowerCase()}</strong>. Measured: <strong>{headline.evidence.profiles[0].misses_after_warmup} vs {headline.evidence.profiles[1].misses_after_warmup}</strong> misses, <strong>{headline.evidence.profiles[0].gate_credits} vs {headline.evidence.profiles[1].gate_credits}</strong> gate credits. <span className="headline-mark">{headline.gateCorrect && headline.missesCorrect ? '✓ Both predictions held' : 'Prediction checked'}</span></p><p className="demo-headline-note">When it is wrong, the failure stays on the record too: <button type="button" className="inline-link" onClick={() => go(1)}>see the failed prediction</button>. Across the full evaluation, simple baselines did as well at finding differences, and we show that.</p></div>
      <p className="demo-recording"><strong>Recorded inspection · no new inference.</strong> Saved {data.model.replace('nvidia/', '')} responses from {data.provider}. Model-selected tests replayed outcomes measured beforehand, twice, in isolated containers. This tour starts no model or worker calls.</p>
    </div>
    <nav className="demo-steps" aria-label="Demonstration steps">{steps.map((label, index) => <button key={label} aria-pressed={step === index} onClick={() => go(index)}><span>{String(index + 1).padStart(2, '0')}</span>{label}</button>)}</nav>
    <article className="study-panel demo-scene">
      <span className="overline">{String(step + 1).padStart(2, '0')} / 04</span>
      <h2 ref={heading} tabIndex={-1}>{step === 0 ? 'One changed rule. A measured difference.' : step === 1 ? 'A confident prediction can be impossible.' : step === 2 ? 'Finding a difference is only one score.' : 'The evidence leaves the app with you.'}</h2>
      <p className="demo-lede">{step === 0 ? 'A caching algorithm decides which page to evict. Here, only the timing of its history update changes; requests, forecasts, random tape and the other settings stay fixed.' : step === 1 ? 'On this smaller cache, the model predicted that both counts would differ. They agreed. A necessary-condition check can also explain why a difference was impossible.' : step === 2 ? 'Every scheduled run stays in the comparison, including controls, rejected tests and responses that exhausted their output limit.' : 'Download the frozen inputs, saved model responses, numerical results and verification code. Recompute them with Python, without a key, Docker, network access or credits.'}</p>
      {step < 2 && <SceneEvidence scene={scene} />}
      {step === 0 && <TraceExplorer />}
      {step === 1 && <div className="demo-proof"><strong>Why the prediction contradicts the rules</strong><p>A support miss requires U≥1, and saved history Y≤k. With {scene.capacity} slots, (Y+2)/e−2 is below 1, so the gate cannot activate under either timing rule. The identical eviction rules then give identical miss counts.</p><p>This is a later review. The batch executed these tests and its original scores remain unchanged.</p></div>}
      {step === 2 && <><div className="study-scroll" tabIndex={0} role="region" aria-label="Policy comparison table"><table className="study-table"><thead><tr><th>Policy</th><th>Finite differences found / available</th><th>Both predictions correct</th><th>Model calls</th></tr></thead><tbody>{data.policies.map(row => <tr key={row.policy}><th scope="row">{policyLabels[row.policy]}</th><td>{row.differences_found} / {row.difference_tasks}</td><td>{row.correct_predictions} / {row.predictions_checked}</td><td>{row.inference_requests}</td></tr>)}</tbody></table></div><div className="demo-proof"><strong>No advantage over the contract heuristic is established.</strong><p>The adaptive model found both available finite differences, as did the simple baselines. Its predictions remain unreliable. Factual reporting is a shared backend check, not a model reasoning score.</p></div><p className="study-caption">{data.batch_calls} model calls · {data.batch_usage.total_tokens.toLocaleString()} reported tokens · two truncated fixed-policy responses retained · no retries. One repeat in one known generator cannot establish a general ranking.</p><button className="button button-secondary" onClick={onEvaluation}>Inspect all tasks and policies →</button></>}
      {step === 3 && <><div className="study-stats"><div><strong>{data.oracle.profiles_checked}</strong><span>distinct profiles independently checked</span></div><div><strong>{data.oracle.post_warmup_events_checked.toLocaleString()}</strong><span>post-warmup events checked</span></div><div><strong>0</strong><span>model calls needed for replay</span></div></div><p className="study-caption">The independent validator enumerates reachable cache configurations and minimum prefix costs. Hashes check consistency within this package; they do not establish independent authorship.</p><div className="demo-downloads"><a className="button button-primary" href={evidenceHref("/api/source-evaluation/export")}>Download full evaluation replay ↓</a><a className="button button-secondary" href={evidenceHref("/api/prediction-review/export")}>Download later prediction review ↓</a></div><details className="study-details"><summary>Inspect frozen protocol fingerprints</summary><p>Tasks</p><code>{data.task_protocol_sha256}</code><p>Execution and scoring</p><code>{data.execution_protocol_sha256}</code></details><div className="demo-proof"><strong>What remains open</strong><ul>{data.limits.map(limit => <li key={limit}>{limit}</li>)}</ul></div></>}
      <div className="demo-controls"><button className="button button-secondary" disabled={step === 0} onClick={() => go(step - 1)}>← Previous</button><span>Step {step + 1} of {steps.length}</span><button className="button button-primary" onClick={() => go(step === 3 ? 0 : step + 1)}>{step === 3 ? 'Start again ↺' : 'Next →'}</button></div>
    </article>
    {step === 1 && <PredictionReview supplied={data.prediction_review} taskId={scene.task_id} />}
  </section>;
}

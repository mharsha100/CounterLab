import { projectFetch, evidenceHref } from './access';
import { useEffect, useState } from 'react';
import './research.css';
import './evaluation.css';

interface Score {
  difference_available: boolean; difference_found: boolean; experiments_executed: number;
  predictions_checked: number; correct_predictions: number; plans_rejected: number;
  finding_checks: { schema_valid: boolean; evidence_correct: boolean; scope_correct: boolean };
}
interface Attempt {
  accepted: boolean; plan?: { test_id: string; hypothesis: string; predict_difference: boolean };
  evidence?: { test_id: string; metric: string; left_value: number; right_value: number; evidence_id: string };
}
interface Run {
  task_id: string; policy: string; status?: string; review_reason?: string; score: Score;
  inference_requests: number; usage?: { total_tokens: number }; elapsed_seconds?: number;
  attempts: Attempt[]; finding?: { outcome: string }; checked_interpretation?: { outcome: string }; planning_records?: Record<string, unknown>;
}
interface Policy {
  policy: string; runs: number; difference_tasks: number; differences_found: number;
  correct_scoped_findings: number; predictions_checked: number; correct_predictions: number;
  plans_rejected: number; experiments: number; inference_requests: number; reported_tokens: number;
}
interface Task { task_id: string; target_factor: string; metric: string; question: string; evaluation_group: string; candidates: unknown[] }
interface EvaluationData {
  protocol_sha256: string; status: string; export_available: boolean;
  protocol: { tasks: Task[]; limitations: string[]; stop_rule: string; model: string };
  policies: Policy[]; baseline_runs: Run[]; model_runs: Run[];
  oracle_validation: { total_event_comparisons: number; study_profile_comparisons: number; tiny_profile_comparisons: number };
  environment: { paired_tests: number; independent_oracle_profile_checks: number };
  model_summary?: { attempted_inference_requests: number; usage: { total_tokens: number }; interruption: string | null };
  verification?: { numerical_replay_verified: boolean; score_replay_verified: boolean };
}
const names: Record<string, string> = {
  heuristic: 'Simple heuristic', random: 'Seeded random', precommitted: 'Nemotron · fixed plan', adaptive: 'Nemotron · adaptive',
  history: 'History timing', priority: 'Random priorities', prediction: 'Prediction delivery',
  gate_credits: 'Gate credits', misses_cold: 'Misses from empty cache',
  finite_mechanism: 'Finite mechanism', null_control: 'Null control',
  non_comparability: 'Confounded comparisons', insufficient_scope: 'Scope & abstention',
  finite_difference: 'Finite difference', finite_agreement: 'Agreement on tested inputs',
  non_comparable: 'No comparable test', insufficient_evidence: 'Insufficient evidence',
};
const label = (value: string) => names[value] || value.replaceAll('_', ' ');
const number = (value: number) => value.toLocaleString();
const complete = (run: Run) => Object.values(run.score.finding_checks).every(Boolean);

export default function Evaluation() {
  const [data, setData] = useState<EvaluationData | null>(null);
  const [error, setError] = useState('');
  const [taskId, setTaskId] = useState('task_01');
  useEffect(() => {
    const controller = new AbortController();
    projectFetch('/api/evaluation', { signal: controller.signal }).then(async response => {
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || 'Evaluation records could not be verified.');
      setData(body);
    }).catch(cause => { if (cause.name !== 'AbortError') setError(cause.message); });
    return () => controller.abort();
  }, []);
  if (error) return <div className="error-banner" role="alert"><strong>Evaluation unavailable.</strong> {error}</div>;
  if (!data) return <div className="loading-card" role="status"><span className="spinner" /> Replaying the measurements and checking every score…</div>;
  const task = data.protocol.tasks.find(item => item.task_id === taskId)!;
  const runs = [...data.baseline_runs, ...data.model_runs].filter(run => run.task_id === taskId);
  const modelRows = data.policies.filter(row => ['adaptive', 'precommitted'].includes(row.policy));
  const heuristic = data.policies.find(row => row.policy === 'heuristic');
  const advantage = heuristic && modelRows.some(row => row.differences_found > heuristic.differences_found);
  return <section className="research-view evaluation-view">
    <div className="section-title"><div><span className="overline">FROZEN BEFORE THE MODEL SAW THE TESTS</span><h2>Does feedback improve experiment selection?</h2></div><span className="badge badge-green">{data.verification?.score_replay_verified ? 'Measurements & scores replayed' : 'Evaluation pending'}</span></div>
    <p className="section-intro">Eight diagnostic tasks, four selection policies and the same two-test allowance. Compare finding a useful difference, keeping numbers correct and knowing when the evidence is insufficient. Each has its own score.</p>
    <div className="study-stats"><div><strong>{number(data.oracle_validation.total_event_comparisons)}</strong><span>event comparisons against an independent mathematical oracle</span></div><div><strong>{data.environment.paired_tests}</strong><span>paired tests · each measured twice in Docker before evaluation</span></div><div><strong>{data.model_summary?.attempted_inference_requests ?? 0} / 40</strong><span>approved model requests used · no automatic retries</span></div></div>

    <article className="study-panel"><div className="section-title"><div><span className="overline">SEPARATE MEASURES · NO COMPOSITE SCORE</span><h3>Compare the four policies.</h3></div><span className="badge">One repeat per task</span></div>
      <div className="study-scroll"><table className="study-table evaluation-table"><thead><tr><th>Selection policy</th><th>Differences found¹</th><th>Correct findings²</th><th>Predictions correct</th><th>Tests</th><th>Model calls</th><th>Reported tokens</th></tr></thead><tbody>{data.policies.map(row => <tr key={row.policy}><th scope="row">{label(row.policy)}<span className="evaluation-row-note">{row.runs} tasks{row.policy === 'adaptive' ? ' · can use feedback' : row.policy === 'precommitted' ? ' · choices fixed first' : ' · no model'}</span></th><td><strong>{row.differences_found} / {row.difference_tasks}</strong></td><td>{row.correct_scoped_findings} / {row.runs}</td><td>{row.predictions_checked ? `${row.correct_predictions} / ${row.predictions_checked}` : 'Not predicted'}</td><td>{row.experiments}</td><td>{row.inference_requests}</td><td>{number(row.reported_tokens)}</td></tr>)}</tbody></table></div>
      <p className="study-caption">¹ Only tasks where at least one admissible option has a finite difference enter this denominator. Agreement on the tested inputs can still be a correct scoped finding. ² Requires valid structure, exact evidence references and correct scope or abstention.</p>
      <div className="study-note"><strong>{data.model_runs.length ? advantage ? 'Any observed advantage is limited to these eight tasks.' : 'These results do not establish better selection than the simple heuristic.' : 'The model batch has not been published yet.'}</strong><p>The simple baselines use a deterministic numeric reporter. Their finding scores do not measure LLM summarization. Model truncations and other failures remain in the denominator; free-text hypotheses are unverified proposals.</p></div>
      <p className="study-caption">New seeds in known generators, one adapter and correlated tasks. These counts provide a development diagnostic, not statistical confidence or a general ranking of models.</p>
    </article>

    <article className="study-panel"><div className="section-title"><div><span className="overline">ALL EIGHT TASKS · INCLUDING FAILURES</span><h3>Inspect the decisions and evidence.</h3></div></div>
      <div className="study-controls"><label className="study-scenario-select">Task<select value={taskId} onChange={event => setTaskId(event.target.value)}>{data.protocol.tasks.map(item => <option key={item.task_id} value={item.task_id}>{item.task_id.replace('task_', '')} · {label(item.evaluation_group)} · {label(item.target_factor)} · {label(item.metric)}</option>)}</select></label></div>
      <p className="evaluation-question">{task.question}</p>
      <div className="evaluation-runs">{['heuristic', 'random', 'precommitted', 'adaptive'].map(policy => {
        const run = runs.find(item => item.policy === policy);
        if (!run) return <div className="evaluation-run" key={policy}><h4>{label(policy)}</h4><p>Not completed. No result fabricated.</p></div>;
        return <article className="evaluation-run" key={policy}><div className="section-title"><h4>{label(policy)}</h4><span className={`badge ${complete(run) ? 'badge-green' : 'badge-amber'}`}>{complete(run) ? 'Scoped finding correct' : 'Review needed'}</span></div>
          <p className="evaluation-outcome">{run.finding ? label(run.finding.outcome) : 'No complete finding'}</p>
          {run.checked_interpretation && !complete(run) && <p className="evaluation-review"><strong>Verified interpretation:</strong> {label(run.checked_interpretation.outcome)}. The original model answer above is preserved and failed the checks below.</p>}
          <p className="study-caption">{run.score.experiments_executed} tests · {run.inference_requests} model calls{run.elapsed_seconds != null ? ` · ${run.elapsed_seconds.toFixed(1)}s` : ''}{run.score.plans_rejected ? ` · ${run.score.plans_rejected} rejected plans` : ''}</p>
          {run.review_reason && <p className="evaluation-review">{label(run.review_reason)}</p>}
          {run.attempts.length === 0 && <p className="study-caption">No experiment executed. Inspect the saved response and scope checks below.</p>}
          {run.attempts.map((attempt, index) => <div className="evaluation-attempt" key={index}><strong>{attempt.plan?.test_id || attempt.evidence?.test_id} · {attempt.accepted ? 'Measured' : 'Rejected before measurement'}</strong>{attempt.evidence && <p>{label(attempt.evidence.metric)}: <b>{attempt.evidence.left_value}</b> vs <b>{attempt.evidence.right_value}</b></p>}{attempt.plan && <details><summary>Precommitted prediction & proposal</summary><p>Predicted: {attempt.plan.predict_difference ? 'difference' : 'agreement'}</p><p>{attempt.plan.hypothesis}</p><small>Model proposal · not a verified explanation</small></details>}</div>)}
          <div className="evaluation-checks">{Object.entries(run.score.finding_checks).map(([key, value]) => <span key={key} className={value ? 'check-pass' : 'check-fail'}>{value ? '✓' : '—'} {label(key)}</span>)}</div>
          <details className="study-details"><summary>Inspect the complete saved run</summary><pre>{JSON.stringify(run, null, 2)}</pre></details>
        </article>;
      })}</div>
      <details className="study-details"><summary>Inspect every candidate, including unselected options</summary><pre>{JSON.stringify(task.candidates, null, 2)}</pre></details>
    </article>

    <article className="study-panel"><div className="section-title"><h3>What was independently checked?</h3><span className="badge">Finite mathematical fidelity</span></div><p className="study-caption">A second implementation enumerates reachable cache configurations and their minimum costs. It does not use the production layer representation. It matched {data.oracle_validation.study_profile_comparisons} study profiles and {number(data.oracle_validation.tiny_profile_comparisons)} exhaustive small profiles, including gate decisions, legal victims, budgets and cache states. The evaluation adds {data.environment.independent_oracle_profile_checks} profile checks.</p>
      <p className="study-caption">This validates our finite mathematical contract. Fidelity to all external implementation regimes, reproduction of the published reports and the asymptotic research claim remain open.</p>
      <details className="study-details"><summary>Read the frozen rules and limitations</summary><p>{data.protocol.stop_rule}</p><ul>{data.protocol.limitations.map(limit => <li key={limit}>{limit}</li>)}</ul><p>Model: {data.protocol.model}. Up to 8,192 output tokens per call; at most 40 calls total. The evaluation reveals a hidden, previously measured result after selection. Timing excludes fresh Docker execution. Opening this page spends no credits.</p></details>
      <div className="study-fingerprint"><span className="small-label">FROZEN EVALUATION PROTOCOL · SHA-256</span><code>{data.protocol_sha256}</code></div>
      {data.export_available && <div className="export-panel"><div><h3>Recompute every measurement and score.</h3><p>Includes frozen inputs, saved plans, failures, numerical code and the independent validation receipt. The portable replay uses no API key or credits; it does not regenerate model replies or rerun the full oracle validation.</p></div><a className="button button-primary" href={evidenceHref("/api/evaluation/export")}>Download evaluation & replay ↓</a></div>}
    </article>
  </section>;
}

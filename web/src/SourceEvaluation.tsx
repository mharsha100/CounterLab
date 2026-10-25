import { projectFetch, evidenceHref } from './access';
import { useEffect, useState } from 'react';
import './research.css';
import './evaluation.css';
import PredictionReview from './PredictionReview';

interface Profile { history: string; tau: number; misses_after_warmup: number; gate_credits: number; trace_sha256: string }
interface Measurement { test_id: string; role: string; seed: number; profiles: Profile[]; evidence_id: string; input_sha256: string; warmup_length: number }
interface Policy { policy: string; runs: number; completed_runs: number; not_run: number; difference_tasks: number; differences_found: number;
  target_tests: number; control_tests: number; plans_rejected: number; predictions_checked: number; correct_predictions: number; planning_failures: number; inference_requests: number; reported_tokens: number }
interface Run { task_id: string; policy: string; status: string; review_reason?: string;
  score: { target_tests: number; control_tests: number; correct_predictions: number; predictions_checked: number };
  attempts: unknown[]; evidence_report: { summary: string; outcome: string }; planning_records: unknown[] }
interface Data {
  status: string; task_protocol_sha256: string; execution_protocol_sha256: string;
  tasks: { task_id: string; capacity: number; horizon: number; question: string; question_scope: string; options: unknown[] }[];
  oracle: { full_trace: boolean; profiles_checked: number; post_warmup_events_checked: number; distinct_seed_batches: number };
  environment_tests: number; isolated_replays: number; policies: Policy[]; baseline_runs: Run[];
  model_results: null | { status: string; runs: Run[]; attempted_inference_requests: number; uncompleted_runs: number; usage: { total_tokens?: number } };
  reference_tests: { key: string; measurement: Measurement }[]; maximum_model_calls: number; output_cap: number;
  verification: { note: string }; limitations: string[]; execution_rules: unknown;
}
const labels: Record<string, string> = { adaptive_two_turn: 'Nemotron · adaptive', precommitted_two_choices: 'Nemotron · fixed choices', contract_heuristic: 'Contract heuristic', seeded_random: 'Seeded random' };
const signed = (n: number) => n > 0 ? `+${n}` : String(n);

export default function SourceEvaluation() {
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState('source_task_01');
  useEffect(() => {
    const controller = new AbortController();
    projectFetch('/api/source-evaluation', { signal: controller.signal }).then(async response => {
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || 'The source evaluation could not be verified.');
      setData(body);
    }).catch(cause => { if (cause.name !== 'AbortError') setError(cause.message); });
    return () => controller.abort();
  }, []);
  if (error) return <p className="error-banner" role="alert">{error}</p>;
  if (!data) return <p className="section-intro" role="status">Verifying fresh source measurements, receipts and scores…</p>;
  const task = data.tasks.find(row => row.task_id === selected)!;
  const tests = data.reference_tests.filter(row => row.key.startsWith(`${selected}/`));
  const runs = [...data.baseline_runs, ...(data.model_results?.runs || [])].filter(run => run.task_id === selected);
  return <section className="research-view evaluation-view fresh-source-evaluation">
    <div className="section-title"><div><span className="overline">FROZEN SOURCE-DERIVED DIAGNOSTICS</span><h2>Verify the experiment. Then measure planning.</h2></div><span className="badge">{data.model_results ? `Model batch: ${data.model_results.status}` : 'Model evaluation not run'}</span></div>
    <p className="section-intro">Eight fresh conditions in the known source-derived generator. The task and execution rules were frozen before these outcomes were measured. Both simple baselines use the same tests, stopping rule and factual reporter as the model policies.</p>
    <div className="study-stats"><div><strong>{data.environment_tests}</strong><span>admissible options · all retained</span></div><div><strong>{data.isolated_replays}</strong><span>actual isolated executions</span></div><div><strong>{data.oracle.post_warmup_events_checked.toLocaleString()}</strong><span>full-trace independent event checks</span></div></div>
    <article className="study-panel"><div className="section-title"><h3>{data.model_results ? 'Measured policy results' : 'Reference outcomes ready; model scores pending.'}</h3><span className="badge">Shared deterministic reporting</span></div>
      {!data.model_results && <div className="study-note"><strong>No new model-performance claim.</strong><p>The table contains zero-inference baselines only. A new batch requires separate approval: at most {data.maximum_model_calls} calls × {data.output_cap.toLocaleString()} output tokens, plus input tokens, with no automatic retries. Opening this page starts no model calls.</p></div>}
      {data.model_results && <p className="study-caption">{data.model_results.attempted_inference_requests} attempted calls · {data.model_results.usage.total_tokens?.toLocaleString() ?? 'Unreported'} reported tokens · {data.policies.filter(row => row.inference_requests > 0).reduce((total,row) => total + row.planning_failures,0)} planning failures retained. One repeat cannot establish a general model ranking.</p>}
      <div className="study-scroll"><table className="study-table evaluation-table"><thead><tr><th>Policy</th><th>Differences found / available</th><th>Target tests</th><th>Controls</th><th>Rejected plans</th><th>Both predictions correct</th><th>Planning failures</th><th>Model calls</th></tr></thead><tbody>{data.policies.map(row => <tr key={row.policy}><th scope="row">{labels[row.policy]}<span className="evaluation-row-note">{row.runs} scheduled runs · {row.not_run} not run</span></th><td><strong>{row.difference_tasks ? `${row.differences_found} / ${row.difference_tasks}` : '—'}</strong></td><td>{row.target_tests}</td><td>{row.control_tests}</td><td>{row.plans_rejected}</td><td>{row.correct_predictions} / {row.predictions_checked}</td><td>{row.planning_failures}</td><td>{row.inference_requests}</td></tr>)}</tbody></table></div>
      <p className="study-caption">A difference means either miss counts or gate credits differ in an admissible history test. Asymptotic questions are excluded from the difference denominator. Baseline predictions are a frozen, evidence-free “both agree” guess; selection and prediction scores stay separate. Scope and citation integrity come from the shared backend.</p>
    </article>
    <article className="study-panel"><div className="section-title"><h3>Inspect every reference outcome.</h3><span className="badge">Nulls and controls retained</span></div><label className="source-history" htmlFor="fresh-source-task">Frozen task<select id="fresh-source-task" value={selected} onChange={event => setSelected(event.target.value)}>{data.tasks.map(row => <option key={row.task_id} value={row.task_id}>{row.task_id.replaceAll('_',' ')} · {row.capacity} slots · {row.horizon.toLocaleString()} requests · {row.question_scope}</option>)}</select></label>
      <p className="evaluation-question">{task.question}</p><p className="study-caption">These premeasured outcomes remain outside model prompts until a test is chosen. A repeat control checks identical settings; it cannot answer the history question.</p>
      <div className="study-scroll"><table className="study-table source-reference-table"><thead><tr><th>Allowed test</th><th>Purpose</th><th>Seed</th><th>Left misses</th><th>Right misses</th><th>Miss difference</th><th>Gate difference</th></tr></thead><tbody>{tests.map(({ key, measurement: evidence }) => <tr key={key}><th scope="row">{evidence.test_id.replaceAll('_', ' ')}</th><td>{evidence.role === 'repeat_control' ? 'Repeat control' : 'History intervention'}</td><td>{evidence.seed}</td><td>{evidence.profiles[0].misses_after_warmup}</td><td>{evidence.profiles[1].misses_after_warmup}</td><td>{signed(evidence.profiles[1].misses_after_warmup-evidence.profiles[0].misses_after_warmup)}</td><td>{signed(evidence.profiles[1].gate_credits-evidence.profiles[0].gate_credits)}</td></tr>)}</tbody></table></div>
      <p className="study-caption">History intervention: left updates after every request; right updates after misses. Repeat control: both update after every request. Differences are right minus left. Costs exclude each trace’s full warmup. Unadmitted options do not have fabricated observations.</p>
      <details className="study-details"><summary>Inspect all options, measurements and fingerprints for this task</summary><pre>{JSON.stringify({ task, tests },null,2)}</pre></details>
      <div className="evaluation-runs">{runs.map(run => <div className="evaluation-run" key={run.policy}><h4>{labels[run.policy]}</h4><p className="study-caption">{run.status.replaceAll('_',' ')}</p><p className="evaluation-outcome">{run.evidence_report.summary}</p><p className="study-caption">{run.score.target_tests} target tests · {run.score.control_tests} controls · both predictions correct on {run.score.correct_predictions} / {run.score.predictions_checked} executed plans.</p>{run.review_reason && <p className="evaluation-review">{run.review_reason === 'incomplete_plan_not_retried' ? 'The response hit its output limit before a complete plan was accepted. No retry was run.' : 'The planning record needs review. Accepted measurements are retained.'}</p>}<details className="study-details"><summary>Inspect choices, complete report and separate scores</summary><pre>{JSON.stringify(run,null,2)}</pre></details></div>)}</div>
    </article>
    <article className="study-panel"><h3>What the verification establishes</h3><p className="study-caption">{data.oracle.profiles_checked} distinct algorithm profiles matched the independent cache-cost oracle over every post-warmup event. The validator enumerates reachable cache configurations and minimum prefix costs; it does not use the production layer algorithm.</p><p className="study-caption">{data.verification.note}</p>
      <ul>{data.limitations.map(limit => <li key={limit}>{limit}</li>)}</ul><p className="study-caption">Fixed selection commits both choices before any execution feedback and pays for unused responses. Adaptive selection receives the first result before its follow-up. Heuristic and random selection cannot access the outcome table. All policies preserve rejected plans and use at most two submitted choices.</p>
      <details className="study-details"><summary>Inspect frozen execution, fairness and scoring rules</summary><pre>{JSON.stringify(data.execution_rules,null,2)}</pre></details>
      <div className="study-fingerprint"><span className="small-label">TASK PROTOCOL · SHA-256</span><code>{data.task_protocol_sha256}</code><span className="small-label">EXECUTION RULES · FROZEN BEFORE OUTCOMES</span><code>{data.execution_protocol_sha256}</code></div>
      <div className="export-panel"><div><h3>Replay all measurements and scores.</h3><p>Includes the frozen inputs, every allowed observation, independent full-trace validator and policy records. Standard-library Python; no API key, Docker, network or credits.</p></div><a className="button button-primary" href={evidenceHref("/api/source-evaluation/export")}>Download evaluation replay ↓</a></div>
    </article>
    <PredictionReview taskId={selected} />
  </section>;
}

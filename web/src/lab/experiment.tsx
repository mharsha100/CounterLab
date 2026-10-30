import { useEffect, useRef, useState } from 'react';
import { failureMessage, niceTicks, plural, wrapLabel } from '../format';
import type { Expected, Experiment, Stat } from './data';
import { num } from './data';
import { Badge, Icon } from './ui';

export function expectationText(item: Expected, labels: Record<string, string>) {
  const left = labels[item.left] ?? item.left, right = labels[item.right] ?? item.right;
  if (item.relation === 'equal') return `${left} ≈ ${right} (within ±${num(item.tolerance)})`;
  return `${left} ${item.relation === 'greater' ? '>' : '<'} ${right}${item.tolerance ? ` by more than ${num(item.tolerance)}` : ''}`;
}
const verdictTone = (status: string) => status === 'held' || status === 'consistent' ? 'good' : status === 'failed' || status === 'contradicted' ? 'bad' : 'neutral';
const verdictMark = (status: string) => status === 'held' || status === 'consistent' ? '✓' : status === 'failed' || status === 'contradicted' ? '✗' : '–';
/** Why an experiment produced no measurements, from its own record (works for records made before reasons were saved). */
export function notMeasuredReason(experiment: Experiment): string {
  const last = [...(experiment.attempts ?? [])].reverse().find(attempt => attempt.feedback || attempt.repair_failed);
  const failed = last?.feedback?.kind === 'guard_rejection' ? last.feedback.failed_checks ?? [] : [];
  if (failed.length) return `CounterLab\u2019s guard rejected this plan before anything ran, so nothing was measured. Rule not met: ${failed.map(check => check.message).join(' ')}`;
  if (last?.repair_failed) return `${failureMessage('repair_failed')} (${failureMessage(last.repair_failed)})`;
  if (last?.feedback?.reason) return `${failureMessage(last.feedback.reason)} Nothing was measured.`;
  return failureMessage(experiment.reason ?? 'not_measured');
}

export function Verdict({ status }: { status: string }) { return <Badge tone={verdictTone(status)}>{verdictMark(status)} {status}</Badge>; }

export function Chart({ metric, label, unit, stats, labels, index }: { metric: string; label: string; unit: string; stats: Record<string, Stat>; labels: Record<string, string>; index: number }) {
  const rows = Object.entries(stats);
  const values = rows.flatMap(([, stat]) => stat.per_seed);
  const frame = useRef<HTMLDivElement>(null);
  const [measured, setMeasured] = useState(640);
  useEffect(() => {
    const element = frame.current;
    if (!element || typeof ResizeObserver === 'undefined') return;
    const observer = new ResizeObserver(entries => setMeasured(Math.max(280, Math.min(960, Math.round(entries[0].contentRect.width)))));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  if (!values.length) return null;
  let low = Math.min(...values), high = Math.max(...values);
  if (low === high) { low -= Math.abs(low) * 0.1 || 1; high += Math.abs(high) * 0.1 || 1; }
  const pad = (high - low) * 0.08; low -= pad; high += pad;
  const width = measured, left = Math.round(Math.min(220, width * 0.36)), right = 18, rowHeight = 44, top = 8, height = top + rows.length * rowHeight + 30;
  const maxLabel = Math.max(8, Math.floor((left - 14) / 6.6));
  const ticks = niceTicks(low, high, width < 420 ? 3 : 5);
  const x = (value: number) => left + ((value - low) / (high - low)) * (width - left - right);
  return <figure className="lab-chart" ref={frame}>
    <figcaption><strong>{label}</strong>{unit && !label.toLowerCase().includes(unit.toLowerCase()) ? ` (${unit})` : ''}<span> · each dot is one seed, the bar is the mean</span></figcaption>
    <svg viewBox={`0 0 ${width} ${height}`} width={width} height={height} role="img" aria-label={`${label} by condition. ${rows.map(([id, s]) => `${labels[id] ?? id}: mean ${num(s.mean)}`).join('; ')}`}>
      {ticks.map(tick => <g key={tick}><line x1={x(tick)} x2={x(tick)} y1={top} y2={height - 24} className="chart-grid" /><text x={x(tick)} y={height - 8} className="lab-axis" textAnchor="middle">{num(tick)}</text></g>)}
      {rows.map(([id, stat], row) => {
        const y = top + row * rowHeight + rowHeight / 2;
        return <g key={id}>
          <text x={left - 12} y={y + 4} className="lab-row-label" textAnchor="end"><title>{labels[id] ?? id}</title>
            {wrapLabel(labels[id] ?? id, maxLabel).map((line, line_index, all) => <tspan key={line_index} x={left - 12} dy={line_index === 0 ? (all.length - 1) * -8 : 16}>{line}</tspan>)}</text>
          {stat.min !== null && stat.max !== null && <line x1={x(stat.min)} x2={x(stat.max)} y1={y} y2={y} className="lab-range" />}
          {stat.per_seed.map((value, seed) => <circle key={seed} cx={x(value)} cy={y} r={4.5} className="lab-dot"><title>{`${labels[id] ?? id}, seed ${seed + 1}: ${num(value)}`}</title></circle>)}
          {stat.mean !== null && <rect x={x(stat.mean) - 1.5} y={y - 12} width={3} height={24} rx={1.5} className="lab-mean"><title>{`${labels[id] ?? id} mean: ${num(stat.mean)}`}</title></rect>}
        </g>;
      })}
    </svg>
    <div className="table-scroll" tabIndex={0} role="region" aria-label={`Experiment ${index}: ${label} table`}><table className="data-table">
      <thead><tr><th scope="col">Condition</th><th scope="col">Mean</th><th scope="col">SD</th><th scope="col">Min</th><th scope="col">Max</th><th scope="col">Seeds</th></tr></thead>
      <tbody>{rows.map(([id, stat]) => <tr key={id}><th scope="row">{labels[id] ?? id}</th><td>{num(stat.mean)}</td><td>{num(stat.std)}</td><td>{num(stat.min)}</td><td>{num(stat.max)}</td><td>{stat.n}</td></tr>)}</tbody>
    </table></div>
    <span className="visually-hidden">{metric}</span>
  </figure>;
}

export function ExperimentView({ experiment, recorded, simulated = false }: { experiment: Experiment; recorded: boolean; simulated?: boolean }) {
  const author = simulated ? 'The simulated planner' : 'Nemotron';
  const plan = experiment.plan;
  if (!plan) return <section className="panel"><h2 className="panel-title">Experiment {experiment.index} was not designed</h2>
    <p className="muted-text">Nemotron did not return a usable design for this step, so nothing was committed or run. The saved requests are in the downloadable record.</p></section>;
  const labels = Object.fromEntries(plan.conditions.map(c => [c.id, c.label]));
  const metrics = Object.fromEntries(plan.metrics.map(m => [m.id, m]));
  const evaluation = experiment.evaluation;
  const explanationStatus = Object.fromEntries((evaluation?.explanations ?? []).map(e => [e.id, e.status]));
  return <article className="experiment" aria-labelledby={`experiment-${experiment.index}`}>
    <header className="experiment-head">
      <div><p className="eyebrow">Experiment {experiment.index}{experiment.index > 1 ? ' · follow-up' : ''}</p><h2 id={`experiment-${experiment.index}`}>{plan.title}</h2></div>
      {experiment.status && <Badge tone={experiment.status === 'completed' ? 'good' : 'warn'} dot>{experiment.status === 'completed' ? 'Measured and reproduced' : experiment.status === 'not_measured' ? 'Not measured' : 'Needs review'}</Badge>}
    </header>
    {experiment.status === 'not_measured' && <p className="alert" role="note"><Icon name="alert" /><span>{notMeasuredReason(experiment)}</span></p>}

    <section className="panel claim">
      <p className="label">Claim under test <span>from the {plan.claim.source.replaceAll('_', ' ')}</span></p>
      <p className="claim-text">{plan.claim.statement}</p>
      {plan.claim.evidence_quote && <blockquote>“{plan.claim.evidence_quote}”</blockquote>}
      <p className="claim-factor"><strong>One factor changes:</strong> {plan.factor}</p>
    </section>

    <section className="panel committed" aria-label={`Experiment ${experiment.index}: committed before execution`}>
      <div className="committed-head"><span className="seal"><Icon name="shield" size={14} /> Committed before anything ran</span>
        <span className="mono-meta">{experiment.committed_at ? new Date(experiment.committed_at).toLocaleString() : ''} · plan {experiment.plan_sha256?.slice(0, 12)}</span></div>
      <ol className="explanations">{plan.explanations.map(explanation => <li key={explanation.id} className={explanation.id === plan.bet ? 'is-bet' : ''}>
        <div className="explanation-head"><strong>{explanation.id}</strong>{explanation.id === plan.bet && <Badge tone="brand">{simulated ? 'Committed bet' : 'Nemotron’s bet'}</Badge>}
          {explanationStatus[explanation.id] && <Verdict status={explanationStatus[explanation.id]} />}</div>
        <p>{explanation.statement}</p>
        <ul>{explanation.expected.map((item, index) => <li key={index}>Expects <strong>{metrics[item.metric]?.label ?? item.metric}</strong>: {expectationText(item, labels)}</li>)}</ul>
      </li>)}</ol>
    </section>

    <div className="design-grid">
      <section className="panel"><p className="label">Conditions</p><ul className="def-list">{plan.conditions.map(c => <li key={c.id}><strong>{c.label}</strong><span>{c.description}</span></li>)}</ul></section>
      <section className="panel"><p className="label">Metrics</p><ul className="def-list">{plan.metrics.map(m => <li key={m.id}><strong>{m.label}</strong><span>{m.description}</span></li>)}</ul></section>
      <section className="panel"><p className="label">Paired seeds</p><p className="mono-meta">{plan.seeds.join(', ')}</p><p className="label spaced">How the inputs are used</p><p className="small-text">{plan.implementation_note}</p></section>
    </div>

    {experiment.attempts?.length > 0 && <details className="disclosure" open={!evaluation}>
      <summary>Checks and repairs before measurement <span className="count">{plural(experiment.attempts.length, 'attempt')}</span></summary>
      <ol className="attempts">{experiment.attempts.map(attempt => <li key={attempt.number}>
        <strong>Attempt {attempt.number}</strong>
        {attempt.repair_failed && <p>Repair failed: {failureMessage(attempt.repair_failed)}</p>}
        {attempt.admission && <div className="checks">{attempt.admission.checks.map(check => <span key={check.check} className={check.passed ? 'check-ok' : 'check-no'} title={check.message}>
          {check.passed ? '✓' : '✗'} {check.check.replaceAll('_', ' ')}</span>)}</div>}
        {attempt.feedback?.failed_checks?.map(check => <p key={check.check} className="feedback">{check.message}</p>)}
        {attempt.run && <p>Sandbox run: {attempt.run.status.replaceAll('_', ' ')}{attempt.run.failed_calls ? ` (${attempt.run.failed_calls} of ${attempt.run.rows} calls failed)` : ''}{attempt.repeat ? `; repeat ${attempt.repeat.status}` : ''}.</p>}
        {attempt.feedback?.examples?.[0] && <pre tabIndex={0}>{attempt.feedback.examples[0].error.split('\n').slice(-6).join('\n')}</pre>}
        {attempt.feedback?.traceback && <pre tabIndex={0}>{attempt.feedback.traceback.split('\n').slice(-6).join('\n')}</pre>}
        {attempt.feedback?.reason && <p>{failureMessage(attempt.feedback.reason)}</p>}
        {attempt.repair_summary && <p className="repair">{author} repaired the harness: {attempt.repair_summary}</p>}
      </li>)}</ol>
    </details>}

    {evaluation && <section className="results" aria-label={`Experiment ${experiment.index} results`}>
      <div className="badge-row">
        <Badge tone={evaluation.complete ? 'good' : 'warn'}>{evaluation.complete ? '✓ Every condition and seed measured' : 'Some measurements failed'}</Badge>
        <Badge tone={evaluation.reproduced ? 'good' : 'warn'}>{evaluation.reproduced ? '✓ Repeat run identical' : 'Repeat run differed'}</Badge>
        <Badge tone={evaluation.bet.outcome === 'held' ? 'good' : evaluation.bet.outcome === 'failed' ? 'bad' : 'neutral'}>Bet {evaluation.bet.explanation}: {evaluation.bet.outcome}</Badge>
      </div>
      {plan.metrics.map(metric => <Chart key={metric.id} metric={metric.id} label={metric.label} unit={metric.unit} stats={evaluation.measurements[metric.id] ?? {}} labels={labels} index={experiment.index} />)}
      <div className="table-scroll" tabIndex={0} role="region" aria-label={`Experiment ${experiment.index}: expectations compared with measurements`}><table className="data-table verdicts">
        <thead><tr><th scope="col">Explanation</th><th scope="col">Expected</th><th scope="col">Measured means</th><th scope="col">Seeds agreeing</th><th scope="col">Sign test p</th><th scope="col">Verdict</th></tr></thead>
        <tbody>{evaluation.verdicts.map((verdict, index) => <tr key={index}><th scope="row">{verdict.explanation}</th>
          <td>{metrics[verdict.metric]?.label}: {expectationText(verdict, labels)}</td>
          <td className="num">{verdict.left_mean !== undefined ? `${num(verdict.left_mean)} vs ${num(verdict.right_mean)}` : verdict.reason}</td>
          <td className="num">{verdict.seeds_agreeing !== undefined ? `${verdict.seeds_agreeing}/${verdict.seeds_compared}` : '—'}</td>
          <td className="num">{verdict.sign_test_p ?? '—'}</td>
          <td><Verdict status={verdict.status} /></td></tr>)}</tbody>
      </table></div>
      <div className="finding2"><p className="label">Finding <span>written by CounterLab from the measurements, not by the model</span></p>
        <ul>{evaluation.finding.map(line => <li key={line}>{line}</li>)}</ul></div>
      {evaluation.errors.length > 0 && <details className="disclosure"><summary>Measurement errors <span className="count">{evaluation.errors.length}</span></summary>
        {evaluation.errors.map((item, index) => <pre key={index} tabIndex={0}>{`${item.condition}, seed ${item.seed}\n${item.error.split('\n').slice(-5).join('\n')}`}</pre>)}</details>}
    </section>}

    {experiment.harness_code && <details className="disclosure code">
      <summary>{simulated ? 'Experiment code (simulated planning)' : 'Experiment code Nemotron wrote'} <span className="count">{experiment.harness_code.split('\n').length} lines</span></summary>
      <pre tabIndex={0}>{experiment.harness_code}</pre>
      <p className="small-text">Ran in {experiment.sandbox?.isolation === 'docker_no_network' ? 'an isolated Docker container: no network, read-only system, non-root, CPU/memory/time limits' : experiment.sandbox?.mode === 'local_process' ? 'a local process without network isolation (opt-in development mode)' : 'the sandbox'}
        {experiment.runtime?.python ? ` · Python ${experiment.runtime.python}` : ''}{experiment.sandbox?.packages ? ` · ${Object.entries(experiment.sandbox.packages).map(([k, v]) => `${k} ${v}`).join(', ')}` : ''}.
        {recorded ? '' : ' CounterLab calls measure() itself with identical seeds for every condition.'}</p>
      {experiment.harness_output_tail && <><p className="label">Harness output</p><pre tabIndex={0}>{experiment.harness_output_tail}</pre></>}
    </details>}
  </article>;
}

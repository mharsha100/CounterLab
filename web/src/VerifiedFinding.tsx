import { useState } from 'react';
import type { Investigation } from './types';
import './finding.css';

const names: Record<string, string> = { finite_difference: 'A difference on the tested inputs.',
  finite_agreement: 'Agreement on the tested inputs.', non_comparable: 'These tests cannot isolate the factor.',
  insufficient_evidence: 'There is not enough measured evidence.' };

export default function VerifiedFinding({ record }: { record: Investigation }) {
  const [inspect, setInspect] = useState(false);
  const report = record.evidence_report;
  if (!report) return null;
  const interrupted = ['failed', 'needs_review'].includes(record.state);
  return <article className="verified-finding">
    <div className="verified-finding-top"><span className="overline">FINDING FROM VERIFIED MEASUREMENTS</span><span className="badge badge-green">No model-generated counts</span></div>
    <h3>{names[report.outcome] || report.summary}</h3>
    <p>{report.summary} This describes the measured metrics in our reviewed reference implementation.</p>
    {record.provider_mode === 'simulated_provider' && <div className="finding-warning">Offline verification: experiment measurements are real; model planning was simulated. This is not a live Nemotron run.</div>}
    {interrupted && <div className="finding-warning">The investigation stopped early. This report covers only the measurements saved before it stopped.</div>}
    <div className="finding-ledger">{report.measurements.map(row => {
      const attempt = record.attempts.find(item => item.evidence?.evidence_id === row.evidence_id);
      return <div className="finding-ledger-row" key={row.evidence_id}><a href={`#attempt-${attempt?.number}`}>{row.test_id.replace('_', ' ')} <span>↗ inspect measurement</span></a><div className="finding-values">{Object.entries(row.metrics).map(([metric, values]) => <div key={metric}><span>{metric === 'gate_credits' ? 'Gate credits' : 'Misses'}</span><strong>{values.left} <small>vs</small> {values.right}</strong><em>{values.left === values.right ? 'agree' : 'differ'}</em></div>)}</div><code title="Evidence fingerprint">{row.evidence_id}</code></div>;
    })}</div>
    {report.measured_tests === 0 && <p className="finding-warning">No experiment supplied measured evidence. Rejected predictions are not observations.</p>}
    <div className="finding-accounting"><span>{report.measured_tests} measured tests · all cited</span><span>{report.rejected_tests.length} rejected plans · excluded from measurements</span></div>
    <div className="finding-boundary"><strong>What this does not establish</strong><p>Agreement on other inputs, the full published disagreement, and any universal or asymptotic claim remain unresolved. Model hypotheses are still unverified proposals.</p></div>
    {record.model_finding != null && <details className="original-finding"><summary>Inspect the original model answer <span>{record.finding ? 'Passed its original checks' : 'Failed its original checks'}</span></summary><p>This earlier workflow asked the model to generate a final answer. The original response is preserved separately from the factual report above.</p><pre>{JSON.stringify(record.model_finding, null, 2)}</pre></details>}
    <button className="text-button finding-inspect" aria-expanded={inspect} onClick={() => setInspect(!inspect)}>{inspect ? 'Hide' : 'Inspect'} the complete report and citations <span>{inspect ? '↑' : '↓'}</span></button>
    {inspect && <pre className="finding-json">{JSON.stringify(report, null, 2)}</pre>}
    <p className="finding-method">The backend derives this factual report from replayed measurements. Nemotron chooses experiments and proposes hypotheses. New investigations use up to two planning calls and no final reporting call.</p>
  </article>;
}

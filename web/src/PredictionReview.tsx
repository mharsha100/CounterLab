import { projectFetch, evidenceHref } from './access';
import { useEffect, useState } from 'react';
import './demonstration.css';

export interface Review { status: string; capacity: number; test_id: string; contradicted_fields: string[]; expected_differences: Record<string, boolean | null>; proofs: { rule: string; explanation: string }[]; review_sha256: string }
export interface Audit {
  timing: string; audit_sha256: string; scope: string; limits: string[];
  policies: { policy: string; reviewed_plans: number; contradicted_plans: number; contradicted_measured_plans: number; unassessable_planning_responses: number }[];
  reviews: { task_id: string; policy: string; attempt: number; contract_admitted: boolean; was_measured: boolean; review: Review }[];
}
export const policyLabels: Record<string, string> = { adaptive_two_turn: 'Nemotron · adaptive', precommitted_two_choices: 'Nemotron · fixed choices', contract_heuristic: 'Contract heuristic', seeded_random: 'Seeded random' };
const statusLabels: Record<string, string> = { contradicted: 'Contradicted by the rules', required_agreement: 'Agreement required by the rules', not_ruled_out: 'Unresolved by these checks' };

export default function PredictionReview({ supplied, taskId }: { supplied?: Audit; taskId?: string }) {
  const [data, setData] = useState<Audit | null>(supplied || null);
  const [error, setError] = useState('');
  useEffect(() => {
    if (supplied) return;
    const controller = new AbortController();
    projectFetch('/api/prediction-review', { signal: controller.signal }).then(async response => {
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || 'Prediction review unavailable.');
      setData(body);
    }).catch(cause => { if (cause.name !== 'AbortError') setError(cause.message); });
    return () => controller.abort();
  }, [supplied]);
  if (error) return <p role="alert" className="error-banner">{error}</p>;
  if (!data) return <p role="status" className="study-caption">Checking saved predictions against necessary conditions…</p>;
  const rows = data.reviews.filter(row => !taskId || row.task_id === taskId);
  return <article className="study-panel prediction-review">
    <div className="section-title"><div><span className="overline">LATER DEVELOPMENT REVIEW · ORIGINAL SCORES PRESERVED</span><h3>Could the prediction be possible?</h3></div><span className="badge">No outcome lookup</span></div>
    <p className="study-caption">This review reads only each committed plan and its input contract. It can rule out an impossible prediction. Passing the check does not show that a prediction is correct. This was added after the frozen batch; it blocked no historical experiments.</p>
    <div className="study-scroll" tabIndex={0} role="region" aria-label="Prediction review table"><table className="study-table"><thead><tr><th>Policy</th><th>Plans reviewed</th><th>Contradicted</th><th>Of those, measured then</th><th>Incomplete responses</th></tr></thead><tbody>{data.policies.map(row => <tr key={row.policy}><th scope="row">{policyLabels[row.policy]}</th><td>{row.reviewed_plans}</td><td>{row.contradicted_plans}</td><td>{row.contradicted_measured_plans}</td><td>{row.unassessable_planning_responses}</td></tr>)}</tbody></table></div>
    {taskId && <div className="review-list">{rows.map(row => <div className={`review-row ${row.review.status === 'contradicted' ? 'review-contradiction' : ''}`} key={`${row.policy}-${row.attempt}`}><div><strong>{policyLabels[row.policy]} · choice {row.attempt}</strong><span>{row.review.test_id.replaceAll('_', ' ')} · {row.contract_admitted ? row.was_measured ? 'Measured in the original batch' : 'Admitted by contract' : 'Rejected by the original contract'}</span></div><p>{statusLabels[row.review.status]}</p><details><summary>Inspect the reasoning</summary>{row.review.proofs.length ? row.review.proofs.map(proof => <p key={proof.rule}>{proof.explanation}</p>) : <p>No necessary condition here determines the outcome. A valid experiment is needed to learn the counts.</p>}<p>Gate difference: {row.review.expected_differences.predict_gate_difference === false ? 'ruled out' : 'unresolved'}. Miss difference: {row.review.expected_differences.predict_miss_difference === false ? 'ruled out' : 'unresolved'}.</p></details></div>)}</div>}
    <p className="study-caption">This checks two Boolean predictions, not the proposed explanation. Controls remain separate from target evidence. Finite results cannot settle an asymptotic claim.</p>
    <details className="study-details"><summary>Inspect the complete review and its limits</summary><pre tabIndex={0}>{JSON.stringify(taskId ? { ...data, reviews: rows } : data, null, 2)}</pre></details>
    <a className="text-button" href={evidenceHref("/api/prediction-review/export")}>Download review and original evidence replay ↓</a>
  </article>;
}

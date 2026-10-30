import { useEffect, useRef, useState } from 'react';
import { isEvidenceBuild, projectFetch } from './access';
import './research.css';
import './claims.css';

interface Citation { record: string; pointer: string; label: string; value: unknown }
interface Claim {
  id: string; title: string; status: 'documented' | 'measured' | 'open'; label: string;
  view: string; answer: string; scope: string; overstatement: string;
  checks: { label: string; state: 'matched' | 'different' | 'unknown' | 'context'; detail: string }[];
  citations: Citation[]; missing: string[];
}
interface Audit {
  report: { version: string; framing: string; claims: Claim[]; limits: string[];
    records: Record<string, { title: string; route: string; view: string; data_sha256: string }>;
    source_links: { id: string; url: string; sha256: string }[] };
  report_sha256: string;
  verification: { basis: string; full_upstream_artifact_verified_here: boolean; note: string };
}
const stateNames = { matched: 'Matched', different: 'Different', unknown: 'Unknown', context: 'Context' };
const filterNames = { all: 'All questions', measured: 'Measured comparisons', open: 'Open questions' };

export default function ClaimAudit() {
  const [data, setData] = useState<Audit | null>(null);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState<keyof typeof filterNames>('all');
  const [selected, setSelected] = useState('contracts');
  const [download, setDownload] = useState('');
  const heading = useRef<HTMLHeadingElement>(null);
  const focusOnChange = useRef(false);
  useEffect(() => {
    const controller = new AbortController();
    projectFetch('/api/claim-audit', { signal: controller.signal }).then(async response => {
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || 'The claim evidence could not be verified.');
      setData(body);
    }).catch(cause => { if (cause.name !== 'AbortError') setError(cause.message); });
    return () => controller.abort();
  }, []);
  useEffect(() => {
    if (!data) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2) + '\n'], { type: 'application/json' }));
    setDownload(url);
    return () => URL.revokeObjectURL(url);
  }, [data]);
  useEffect(() => {
    if (focusOnChange.current) { heading.current?.focus(); focusOnChange.current = false; }
  }, [selected, filter]);
  if (error) return <div className="error-banner" role="alert"><strong>Claim audit unavailable.</strong> {error} No conclusions are shown from unverified evidence.</div>;
  if (!data) return <div className="loading-card" role="status"><span className="spinner" /> {isEvidenceBuild ? 'Checking the packaged claim audit…' : 'Checking the sealed source, study and evaluation records…'}</div>;
  const { report } = data;
  const visible = report.claims.filter(claim => filter === 'all' || claim.status === filter);
  const claim = visible.find(item => item.id === selected) || visible[0];
  function choose(id: string) { if (id === selected) { heading.current?.focus(); return; } focusOnChange.current = true; setSelected(id); }
  function changeFilter(next: keyof typeof filterNames) {
    setFilter(next);
    const items = report.claims.filter(item => next === 'all' || item.status === next);
    if (!items.some(item => item.id === selected)) setSelected(items[0].id);
  }
  return <section className="research-view claim-audit">
    <div className="section-title"><div><span className="overline">CLAIM → CONTRACT → EVIDENCE</span><h2>What can we actually conclude?</h2></div><span className="badge">5 bounded questions · 0 new model calls</span></div>
    <p className="section-intro">Follow each answer to its measured or documented basis. A difference in a contract, a matched number and an unresolved question mean different things.</p>
    <div className="claim-legend"><span><i className="claim-dot measured" />Finite measurements</span><span><i className="claim-dot documented" />Source inspection</span><span><i className="claim-dot open" />Evidence still missing</span></div>
    <div className="claim-filters study-tabs" role="group" aria-label="Filter claim questions">{(Object.keys(filterNames) as (keyof typeof filterNames)[]).map(key => <button key={key} aria-pressed={filter === key} onClick={() => changeFilter(key)}>{filterNames[key]} <span>{key === 'all' ? report.claims.length : report.claims.filter(item => item.status === key).length}</span></button>)}</div>
    <div className="claim-layout">
      <div className="claim-questions" role="group" aria-label="Claim questions">{visible.map((item) => <button key={item.id} aria-pressed={claim.id === item.id} onClick={() => choose(item.id)}><span className="claim-question-number">0{report.claims.indexOf(item) + 1}</span><span><strong>{item.title}</strong><small><i className={`claim-dot ${item.status}`} />{item.label}</small></span><span className="claim-arrow" aria-hidden="true">↗</span></button>)}</div>
      <article className={`study-panel claim-detail claim-detail-${claim.status}`} aria-labelledby="claim-answer-heading" key={claim.id}>
        <div className="claim-detail-top"><span className={`claim-status claim-status-${claim.status}`}>{claim.label}</span><span className="small-label">BOUNDED ANSWER</span></div>
        <h3 id="claim-answer-heading" ref={heading} tabIndex={-1}>{claim.title}</h3>
        <p className="claim-answer">{claim.answer}</p><p className="claim-scope">{claim.scope}</p>
        <h4>Check what is comparable.</h4>
        <ul className="claim-checks">{claim.checks.map(check => <li key={check.label}><span className={`claim-check-state claim-check-${check.state}`}>{stateNames[check.state]}</span><div><strong>{check.label}</strong><p>{check.detail}</p></div></li>)}</ul>
        <div className="claim-overstatement"><span className="small-label">THIS WOULD OVERSTATE THE EVIDENCE</span><p>“{claim.overstatement}”</p></div>
        <div className="claim-evidence"><h4>Inspect the evidence behind this answer.</h4>{claim.citations.map((citation, i) => {
          const record = report.records[citation.record];
          return <details key={`${citation.record}:${citation.pointer}`}><summary><span className="claim-citation-number">{i + 1}</span><span>{citation.label}<small>{record.title}</small></span><span aria-hidden="true">+</span></summary><div className="claim-citation-body"><p><strong>Record field</strong><code>{record.route}{citation.pointer}</code></p><pre tabIndex={0}>{JSON.stringify(citation.value, null, 2)}</pre><span className="small-label">COMPACT EVIDENCE BASIS · SHA-256</span><code>{record.data_sha256}</code><a className="text-button" href={`?view=${record.view}`}>Open the complete evidence view →</a></div></details>;
        })}</div>
        <div className="claim-missing"><h4>What would close the remaining gap?</h4>{claim.missing.map(item => <p key={item}>{item}</p>)}</div>
        <a className="button button-primary" href={`?view=${claim.view}`}>Inspect this comparison →</a>
      </article>
    </div>
    <article className="study-panel claim-provenance"><div className="section-title"><h3>Source trail and verification context</h3><span className="badge">No external source code executed</span></div>
      <p>{report.framing}</p><p>{data.verification.note}</p>
      <div className="claim-reference-context"><strong>{data.verification.full_upstream_artifact_verified_here ? `Full upstream numeric file hash-verified ${isEvidenceBuild ? 'at packaging' : 'in this environment'}.` : `Full upstream numeric file not verified ${isEvidenceBuild ? 'at packaging' : 'in this environment'}.`}</strong><p>The three comparison rows are verified against the frozen local record. The full upstream file is omitted from distribution; its replay package explains explicit retrieval.</p></div>
      <details className="study-details"><summary>Inspect all six pinned source links</summary>{report.source_links.map(source => <div className="study-source" key={source.id}><a href={source.url} target="_blank" rel="noreferrer">{source.id.replaceAll('_', ' ')} ↗</a><code>{source.sha256}</code></div>)}</details>
      <ul className="claim-limits">{report.limits.map(limit => <li key={limit}>{limit}</li>)}</ul>
      <div className="claim-export"><div><span className="small-label">DERIVED REPORT · SHA-256</span><code>{data.report_sha256}</code><p>Recheck the downloaded JSON with the full source build:<br /><code>python scripts/check_claim_audit.py --record PATH_TO_JSON</code></p></div>{download && <a className="button button-secondary" href={download} download={`counterlab-claim-audit-${data.report_sha256.slice(0, 12)}.json`}>Save claim audit ↓</a>}</div>
    </article>
  </section>;
}

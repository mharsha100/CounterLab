import { useMemo, useRef, useEffect } from 'react';
import { setParam, useParam } from '../navigation';
import { active, canWrite, exact, num, runTitle, stateLabel, useLab, when, type ListItem } from './data';
import { AppLink, Badge, BetBadge, Empty, Icon, Kbd, Skeleton, StateBadge } from './ui';

const FILTERS = [['', 'All'], ['running', 'Running'], ['completed', 'Completed'], ['needs_review', 'Needs review'], ['stopped', 'Stopped or failed']] as const;

export function matches(item: ListItem, status: string, query: string) {
  const state = active(item.state) ? 'running' : item.state === 'failed' || item.state === 'cancelled' ? 'stopped' : item.state;
  if (status && state !== status) return false;
  const text = `${item.title ?? ''} ${item.question} ${item.id} ${stateLabel(item.state)}`.toLowerCase();
  return query.trim().toLowerCase().split(/\s+/).every(word => text.includes(word));
}

export function RunRows({ items, compact = false }: { items: ListItem[]; compact?: boolean }) {
  return <div className="table-scroll flush"><table className={`run-table ${compact ? 'compact' : ''}`}>
    <caption className="visually-hidden">Investigations, newest first</caption>
    <thead><tr><th scope="col">Investigation</th><th scope="col">Status</th><th scope="col">Committed bets</th>
      {!compact && <th scope="col">Experiments</th>}{!compact && <th scope="col">Requests</th>}<th scope="col">Started</th></tr></thead>
    <tbody>{items.map(item => <tr key={item.id}>
      <td className="run-cell-title"><AppLink route="run" params={{ id: item.id }} className="row-link">{runTitle(item)}</AppLink>
        {item.title && <span className="run-q">{item.question}</span>}
        {(item.provider_mode === 'simulated_provider' || item.kind === 'recorded') && <span className="run-tags">
          {item.provider_mode === 'simulated_provider' && <Badge tone="warn">Simulated planning</Badge>}{item.kind === 'recorded' && <Badge>Recorded</Badge>}</span>}</td>
      <td><StateBadge state={item.state} /></td>
      <td><div className="bet-list">{item.bets.length ? item.bets.map(bet => <BetBadge key={bet.experiment} outcome={bet.outcome} experiment={item.bets.length > 1 ? bet.experiment : undefined} />)
        : <span className="muted-text">{active(item.state) ? 'Pending' : '—'}</span>}</div></td>
      {!compact && <td className="num">{item.experiments ? `${item.experiments_measured} of ${item.experiments} measured` : '—'}</td>}
      {!compact && <td className="num">{num(item.model_calls)}</td>}
      <td className="muted-text nowrap" title={exact(item.created_at)}>{when(item.created_at)}</td>
    </tr>)}</tbody>
  </table></div>;
}

export default function Runs() {
  const { items, loaded, contract, error } = useLab();
  const status = useParam('status');
  const query = useParam('q');
  const search = useRef<HTMLInputElement>(null);
  const shown = useMemo(() => items.filter(item => matches(item, status, query)), [items, status, query]);
  useEffect(() => {
    const focus = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement;
      if (event.key === '/' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName) && !target.isContentEditable) { event.preventDefault(); search.current?.focus(); }
    };
    window.addEventListener('keydown', focus);
    return () => window.removeEventListener('keydown', focus);
  }, []);
  const counts = useMemo(() => Object.fromEntries(FILTERS.map(([key]) => [key, items.filter(item => matches(item, key, '')).length])), [items]);
  return <div className="page">
    <header className="page-head">
      <div><h1 className="page-title" tabIndex={-1}>Investigations</h1><p className="page-sub">Every investigation is sealed with its inputs, committed plans, sandbox measurements and findings.</p></div>
      {canWrite(contract) && <AppLink route="lab" className="btn btn-primary"><Icon name="plus" /> New investigation</AppLink>}
    </header>
    <div className="toolbar">
      <div className="search"><Icon name="search" /><label htmlFor="runs-search" className="visually-hidden">Search investigations</label>
        <input ref={search} id="runs-search" type="search" placeholder="Search by question, title or ID…" value={query} autoComplete="off" spellCheck={false}
          onChange={event => setParam('q', event.target.value)} /><Kbd>/</Kbd></div>
      <div className="segmented" role="group" aria-label="Filter by status">{FILTERS.map(([key, label]) => <button key={key} type="button" aria-pressed={status === key}
        onClick={() => setParam('status', key)}>{label} <span className="count">{counts[key]}</span></button>)}</div>
    </div>
    {error && !items.length && <div className="alert alert-bad" role="alert"><Icon name="alert" /><div><strong>Could not load investigations.</strong> {error}</div></div>}
    {!loaded ? <Skeleton lines={6} /> : shown.length ? <RunRows items={shown} />
      : items.length ? <Empty icon="search" title="No investigations match" action={<button type="button" className="btn btn-secondary" onClick={() => { setParam('q', ''); setParam('status', ''); search.current?.focus(); }}>Clear filters</button>}>
        Try a different word or status.</Empty>
      : <Empty icon="activity" title="No investigations yet" action={canWrite(contract) ? <AppLink route="lab" className="btn btn-primary"><Icon name="plus" /> Start your first investigation</AppLink> : undefined}>
        Upload a paper or code and Nemotron will design an experiment that tests it.</Empty>}
  </div>;
}

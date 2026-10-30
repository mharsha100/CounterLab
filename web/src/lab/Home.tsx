import { useState, type DragEvent } from 'react';
import { isEvidenceBuild, sourceBuildHref } from '../access';
import { navigateTo } from '../navigation';
import { canWrite, guessRole, setDraft, useLab } from './data';
import { RunRows } from './Runs';
import { AppLink, Icon, Kbd, Skeleton } from './ui';

function Checklist() {
  const { contract, items } = useLab();
  if (!contract || !canWrite(contract)) return null;
  const check = contract.connection?.last_check;
  const steps = [
    { done: Boolean(contract.connection?.key_configured && check?.ok), title: 'Connect Nemotron', text: 'Save your Nebius API key and check that Nemotron is available.', route: 'settings' as const, label: 'Open Settings' },
    { done: contract.sandbox.ready, title: 'Prepare the sandbox', text: 'Build the isolated container your code runs in. Docker Desktop must be running.', route: 'settings' as const, label: 'Set up', tab: 'sandbox' },
    { done: items.some(item => item.kind === 'live' && item.state === 'completed'), title: 'Run your first investigation', text: 'Start with an example: three to five Nemotron requests and a few minutes.', route: 'lab' as const, label: 'Try an example', example: contract.examples[0]?.id },
  ];
  if (steps.every(step => step.done)) return null;
  const next = steps.findIndex(step => !step.done);
  return <section className="panel checklist" aria-labelledby="checklist-title">
    <div className="panel-head"><h2 className="panel-title" id="checklist-title">Get set up</h2><span className="muted-text">{steps.filter(step => step.done).length} of 3 done</span></div>
    <ol>{steps.map((step, index) => <li key={step.title} className={step.done ? 'done' : index === next ? 'next' : ''}>
      <span className="check-node" aria-hidden="true">{step.done ? <Icon name="check" size={14} /> : index + 1}</span>
      <div><strong>{step.title}</strong><span>{step.text}</span></div>
      {step.done ? <span className="visually-hidden">Done</span> : <AppLink route={step.route} params={step.tab ? { tab: step.tab } : step.example ? { example: step.example } : {}}
        className={`btn ${index === next ? 'btn-primary' : 'btn-secondary'}`}>{step.label}</AppLink>}
    </li>)}</ol>
  </section>;
}

function QuickDrop() {
  const { contract } = useLab();
  const [over, setOver] = useState(false);
  if (!canWrite(contract)) return null;
  function start(files: File[]) {
    if (!files.length) return;
    setDraft({ files: files.map(file => ({ file, role: guessRole(file.name) })) });
    navigateTo('lab');
  }
  return <div className={`quick-drop ${over ? 'drop-over' : ''}`} onDragOver={event => { event.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
    onDrop={(event: DragEvent) => { event.preventDefault(); setOver(false); start(Array.from(event.dataTransfer.files)); }}>
    <input id="home-files" type="file" multiple className="visually-hidden" onChange={event => start(Array.from(event.target.files ?? []))} />
    <Icon name="upload" size={20} /><span><strong>Drop a paper or code to begin</strong> or <label htmlFor="home-files" className="link-button">choose files</label></span>
  </div>;
}

export default function Home() {
  const { contract, items, loaded } = useLab();
  const live = items.filter(item => item.kind === 'live');
  const pool = live.length ? live : items;
  // Bets and requests are credited to Nemotron only for runs Nemotron actually planned; simulated plans never count.
  const planned = pool.filter(item => item.provider_mode !== 'simulated_provider');
  const simulated = pool.length > 0 && planned.length === 0;
  const credited = simulated ? pool : planned;
  const bets = credited.flatMap(item => item.bets);
  const held = bets.filter(bet => bet.outcome === 'held').length;
  const measured = pool.reduce((sum, item) => sum + item.experiments_measured, 0);
  const requests = credited.reduce((sum, item) => sum + (item.model_calls ?? 0), 0);
  return <div className="page home">
    <header className="home-hero">
      <div>
        <h1 className="page-title display" tabIndex={-1}>Put a research claim to the test.</h1>
        <p className="page-sub">Upload a paper, its code, or two implementations that disagree. NVIDIA Nemotron on Nebius designs the experiment and commits its prediction before anything runs. CounterLab runs it twice in a sealed sandbox and writes the finding only from what it measured.</p>
        <div className="hero-actions">
          {canWrite(contract) ? <><AppLink route="lab" className="btn btn-primary btn-large"><Icon name="plus" /> New investigation</AppLink>
            <span className="muted-text">or press <Kbd>N</Kbd></span></>
            : isEvidenceBuild ? <><a className="btn btn-primary btn-large" href={sourceBuildHref()}><Icon name="download" /> Download CounterLab</a>
              <AppLink route="runs" className="btn btn-secondary btn-large">Browse recorded investigations</AppLink></>
            : <AppLink route="runs" className="btn btn-secondary btn-large">Browse investigations</AppLink>}
        </div>
      </div>
      <QuickDrop />
    </header>
    {isEvidenceBuild && <div className="alert" role="note"><Icon name="alert" /><div><strong>You are viewing the hosted demo.</strong> It shows recorded investigations and makes no model calls. Download CounterLab and add your Nebius key to investigate your own paper or code.</div></div>}
    <Checklist />

    <section className="stats" aria-label={live.length ? 'Your investigations' : 'Recorded investigations'}>
      <div><span className="stat-value">{loaded ? pool.length : '–'}</span><span className="stat-label">{live.length ? 'Investigations' : 'Recorded investigations'}</span></div>
      <div><span className="stat-value">{loaded ? measured : '–'}</span><span className="stat-label">Experiments measured</span></div>
      <div><span className="stat-value">{loaded ? (bets.length ? `${held}/${bets.length}` : '–') : '–'}</span><span className="stat-label">{simulated ? 'Committed bets that held' : 'Nemotron bets that held'}</span></div>
      <div><span className="stat-value">{loaded ? requests : '–'}</span><span className="stat-label">{simulated ? 'Planning requests (simulated)' : 'Nemotron requests'}</span></div>
    </section>

    <section className="section" aria-labelledby="recent-title">
      <div className="section-head"><h2 id="recent-title">Recent investigations</h2>{items.length > 0 && <AppLink route="runs" className="btn btn-quiet">View all <Icon name="arrow" /></AppLink>}</div>
      {!loaded ? <Skeleton lines={4} /> : items.length ? <RunRows items={items.slice(0, 5)} compact />
        : <p className="muted-text">No investigations yet. Start one above or from an example below.</p>}
    </section>

    {contract && contract.examples.length > 0 && <section className="section" aria-labelledby="examples-title">
      <div className="section-head"><h2 id="examples-title">Start from an example</h2></div>
      <div className="example-grid">{contract.examples.map(example => canWrite(contract)
        ? <AppLink key={example.id} route="lab" params={{ example: example.id }} className="example"><strong>{example.title}</strong><span>{example.description}</span>
          <span className="example-files">{example.files.length} files · {example.kind.replaceAll('_', ' ')}</span></AppLink>
        : <div key={example.id} className="example static"><strong>{example.title}</strong><span>{example.description}</span></div>)}</div>
    </section>}

    <section className="section" aria-labelledby="case-title">
      <div className="section-head"><h2 id="case-title">Case study</h2></div>
      <AppLink route="demo" className="case-card"><Icon name="book" size={20} /><div><strong>Learning-augmented paging (ICML 2026)</strong>
        <span>A published disagreement investigated end to end, with a frozen evaluation of Nemotron against zero-inference baselines and eight replay packages.</span></div><Icon name="chevron" /></AppLink>
    </section>
  </div>;
}

import { useEffect, useMemo, useRef, useState, type DragEvent, type FormEvent } from 'react';
import { isEvidenceBuild, sourceBuildHref } from '../access';
import { navigateTo, setParam, useParam } from '../navigation';
import {
  action, active, api, encode, guessRole, kilobytes, refreshLab, runTitle, takeDraft, toast, useLab,
  type Example, type ListItem, type Picked, type Role, type Run,
} from './data';
import { AppLink, Icon, Kbd } from './ui';

const PAPER_TYPES = '.pdf,.md,.markdown,.txt,.tex,.rst';
const ACCEPT = `${PAPER_TYPES},.zip,.py,.ipynb,.c,.cc,.cpp,.h,.hpp,.cu,.js,.ts,.java,.rs,.go,.jl,.r,.m,.json,.csv,.toml,.yaml,.yml`;
const ALLOWANCES: Record<number, string> = { 8192: 'Small: quick designs; may run out on large inputs', 16384: 'Standard: recommended for most inputs', 32768: 'Large: long papers or big repositories' };

export function Readiness({ compact = false }: { compact?: boolean }) {
  const { contract } = useLab();
  if (!contract || isEvidenceBuild || contract.read_only) return null;
  const connection = contract.connection;
  const check = connection?.last_check;
  const keyed = Boolean(connection?.key_configured);
  const nemotron = !keyed ? { tone: 'bad', text: 'Not connected', detail: 'Add your Nebius API key to connect Nemotron.' }
    : check && !check.ok ? { tone: 'bad', text: 'Connection problem', detail: 'The last connection check failed. Open Settings to see why.' }
    : check?.ok ? { tone: 'good', text: 'Connected', detail: `${check.model ?? contract.model} is available.` }
    : { tone: 'neutral', text: 'Key saved', detail: 'The connection is checked before each investigation.' };
  const sandbox = contract.sandbox.ready ? { tone: 'good', text: 'Ready', detail: contract.sandbox.isolation === 'docker_no_network' ? 'Docker · no network · non-root' : 'Local process (not isolated)' }
    : contract.sandbox.setup?.state === 'building' ? { tone: 'run', text: 'Setting up', detail: contract.sandbox.setup.message ?? 'Building the sandbox image' }
    : { tone: 'bad', text: 'Not set up', detail: 'Docker Desktop must be running.' };
  return <section className={`readiness ${compact ? 'compact' : ''}`} aria-label="Readiness">
    <div className="readiness-row"><span className={`status-dot2 ${nemotron.tone}`} aria-hidden="true" /><div><strong>Nemotron · {nemotron.text}</strong><span>{nemotron.detail}</span></div>
      {nemotron.tone !== 'good' && <AppLink route="settings" className="btn btn-quiet">{keyed ? 'Check' : 'Connect'}</AppLink>}</div>
    <div className="readiness-row"><span className={`status-dot2 ${sandbox.tone}`} aria-hidden="true" /><div><strong>Sandbox · {sandbox.text}</strong><span>{sandbox.detail}</span></div>
      {sandbox.tone === 'bad' && <AppLink route="settings" params={{ tab: 'sandbox' }} className="btn btn-quiet">Set up</AppLink>}</div>
  </section>;
}

function DropArea({ onFiles, disabled }: { onFiles: (files: File[]) => void; disabled: boolean }) {
  const [over, setOver] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  function drop(event: DragEvent) { event.preventDefault(); setOver(false); if (!disabled) onFiles(Array.from(event.dataTransfer.files)); }
  return <div className={`drop ${over ? 'drop-over' : ''} ${disabled ? 'drop-off' : ''}`} onDragOver={event => { event.preventDefault(); if (!disabled) setOver(true); }}
    onDragLeave={() => setOver(false)} onDrop={drop}>
    <input ref={input} id="composer-files" type="file" multiple accept={ACCEPT} disabled={disabled} className="visually-hidden"
      onChange={event => { onFiles(Array.from(event.target.files ?? [])); event.target.value = ''; }} />
    <Icon name="upload" size={22} />
    <p><strong>Drop a paper and code here</strong> or <label htmlFor="composer-files" className="link-button">choose files</label></p>
    <span>PDF, Markdown, LaTeX or text papers · Python files or a ZIP per implementation</span>
  </div>;
}

export default function Composer() {
  const { contract, items } = useLab();
  const exampleParam = useParam('example');
  const fromParam = useParam('from');
  const [question, setQuestion] = useState('');
  const [picked, setPicked] = useState<Picked[]>([]);
  const [paperUrl, setPaperUrl] = useState('');
  const [codeUrl, setCodeUrl] = useState('');
  const [showLinks, setShowLinks] = useState(false);
  const [allowance, setAllowance] = useState(16384);
  const [followUp, setFollowUp] = useState(true);
  const [consent, setConsent] = useState(false);
  const [starting, setStarting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [startError, setStartError] = useState('');
  const [formProblem, setFormProblem] = useState('');
  const [reuse, setReuse] = useState<Run | null>(null);
  const requestId = useRef('');
  const questionRef = useRef<HTMLTextAreaElement>(null);
  const inputsRef = useRef<HTMLDivElement>(null);
  const consentRef = useRef<HTMLInputElement>(null);
  const example: Example | null = contract?.examples.find(item => item.id === exampleParam) ?? null;

  useEffect(() => {
    const draft = takeDraft();
    if (draft.files.length) setPicked(draft.files);
    if (draft.question) setQuestion(draft.question);
    if (draft.allowance) setAllowance(draft.allowance);
    if (draft.followUp !== undefined) setFollowUp(draft.followUp);
    requestAnimationFrame(() => { if (!draft.question && window.matchMedia('(min-width: 900px)').matches) questionRef.current?.focus(); });
  }, []);
  useEffect(() => { if (contract) setAllowance(current => contract.output_allowances.includes(current) ? current : contract.default_output_allowance); }, [contract]);
  useEffect(() => { if (example) setQuestion(current => current.trim() ? current : example.question); }, [example?.id]);
  useEffect(() => {
    if (!fromParam) { setReuse(null); return; }
    let cancelled = false;
    api<Run>(`/api/open-investigations/${fromParam}`).then(run => { if (!cancelled) { setReuse(run); setQuestion(current => current || run.request?.question || ''); } })
      .catch(() => { if (!cancelled) { setReuse(null); toast('The earlier investigation could not be loaded, so its inputs are not reused.', 'bad'); setParam('from', ''); } });
    return () => { cancelled = true; };
  }, [fromParam]);

  useEffect(() => { if (!Object.values(errors).some(Boolean)) setFormProblem(''); }, [errors]);

  const running = items.find((item: ListItem) => active(item.state));
  const blocked = !contract ? '' : isEvidenceBuild ? 'hosted' : contract.read_only ? 'read_only' : '';
  const notReady = contract && !blocked ? (!contract.connection?.key_configured ? 'key' : !contract.sandbox.ready ? 'sandbox' : '') : '';
  const totalBytes = picked.reduce((sum, item) => sum + item.file.size, 0);
  const hasInputs = Boolean(reuse || example || picked.length || paperUrl.trim() || codeUrl.trim());
  const disabled = Boolean(blocked) || starting;

  function validate() {
    const next: Record<string, string> = {};
    if (question.trim().length < 10) next.question = 'Describe what the experiment should settle (at least 10 characters).';
    if (!hasInputs) next.inputs = 'Add a paper, some code, a link, or choose an example.';
    if (contract && totalBytes > contract.limits.upload_megabytes * 1_000_000) next.inputs = `Uploads are limited to ${contract.limits.upload_megabytes} MB in total. Put the relevant files in a smaller ZIP.`;
    if (contract && picked.length > contract.limits.files) next.inputs = `Add at most ${contract.limits.files} files; put larger projects in a ZIP.`;
    if (!consent) next.consent = 'Confirm the credit use to start.';
    return next;
  }
  function add(files: File[]) {
    setPicked(current => [...current, ...files.filter(file => !current.some(item => item.file.name === file.name && item.file.size === file.size))
      .map(file => ({ file, role: guessRole(file.name) }))]);
    if (example) setParam('example', '');
    setErrors(current => ({ ...current, inputs: '' })); requestId.current = '';
  }
  function chooseExample(next: Example) {
    setParam('example', next.id); setPicked([]); setPaperUrl(''); setCodeUrl('');
    setQuestion(next.question); requestId.current = ''; setErrors({});
  }
  async function start(event?: FormEvent) {
    event?.preventDefault();
    if (disabled) return;
    setStartError('');
    let found: Record<string, string>;
    try { found = validate(); } catch (cause) {
      setStartError(cause instanceof Error ? cause.message : 'The form could not be checked. Reload the page and try again.');
      return;
    }
    setErrors(found);
    const problems = Object.entries(found).filter(([, value]) => value);
    if (problems.length) {
      const [first] = problems[0];
      const target = first === 'question' ? questionRef.current : first === 'inputs' ? inputsRef.current : consentRef.current;
      target?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      target?.focus({ preventScroll: true });
      const elsewhere = problems.filter(([key]) => key !== 'consent');
      setFormProblem(elsewhere.length ? `Not started yet. ${elsewhere.map(([, value]) => value).join(' ')}` : '');
      return;
    }
    setStarting(true);
    try {
      if (!requestId.current) requestId.current = crypto.randomUUID().replaceAll('-', '');
      const files = await Promise.all(picked.map(async item => ({ name: item.file.name, role: item.role, content_base64: await encode(item.file) })));
      const body = { request_id: requestId.current, confirm_credit_use: true, question: question.trim(), files,
        paper_url: paperUrl.trim() || null, code_url: codeUrl.trim() || null, example_id: example?.id ?? null,
        reuse_inputs_from: reuse?.id ?? null, max_output_tokens: allowance, follow_up: followUp };
      const started = await action<{ id: string }>('/api/open-investigations', 'start-investigation', body);
      requestId.current = '';
      toast('Investigation started. Nemotron is designing the experiment.', 'good');
      refreshLab();
      navigateTo('run', { id: started.id });
    } catch (cause) {
      setStartError(cause instanceof Error ? cause.message : 'The investigation could not be started.');
    } finally { setStarting(false); }
  }

  const exampleCards = useMemo(() => contract?.examples ?? [], [contract]);
  return <div className="page composer-page">
    <header className="page-head">
      <div><h1 className="page-title" tabIndex={-1}>New investigation</h1>
        <p className="page-sub">Bring a paper, the code behind it, or two implementations that disagree. Nemotron designs one controlled experiment and commits its prediction; CounterLab runs it in a sandbox and reports only what it measured.</p></div>
    </header>

    {blocked === 'hosted' && <div className="alert" role="note"><Icon name="alert" /><div><strong>This hosted demo can’t start investigations.</strong> It has no model connection. Download CounterLab and run it with your Nebius key to investigate your own paper or code.
      <div className="alert-actions"><a className="btn btn-primary" href={sourceBuildHref()}><Icon name="download" /> Download CounterLab</a><AppLink route="runs" className="btn btn-secondary">Browse recorded investigations</AppLink></div></div></div>}
    {blocked === 'read_only' && <div className="alert" role="note"><Icon name="alert" /><div><strong>Read-only mode.</strong> Starting investigations is disabled. Restart the app without <code>--read-only</code> to run your own.</div></div>}
    {running && !blocked && <div className="alert alert-run" role="status"><Icon name="activity" /><div><strong>An investigation is running.</strong> One runs at a time; you can prepare this one and start it when the other finishes.
      <div className="alert-actions"><AppLink route="run" params={{ id: running.id }} className="btn btn-secondary">Open “{runTitle(running).slice(0, 48)}”</AppLink></div></div></div>}

    <div className="composer">
      <form className="composer-form" onSubmit={start} noValidate aria-label="New investigation">
        <section className="field-block">
          <label htmlFor="composer-question" className="field-title">What should the experiment settle?</label>
          <p className="field-help" id="question-help">A claim to check, a result that didn’t reproduce, or a disagreement between two implementations. Be specific about what “better” or “correct” means.</p>
          <textarea id="composer-question" ref={questionRef} rows={4} maxLength={contract?.limits.question_characters ?? 2000} value={question} disabled={disabled}
            aria-describedby={`question-help${errors.question ? ' question-error' : ''}`} aria-invalid={Boolean(errors.question)}
            placeholder="e.g. The paper says the new optimizer converges faster as noise grows. Does the released code show that, and is the difference real?"
            onChange={event => { setQuestion(event.target.value); requestId.current = ''; if (errors.question) setErrors(c => ({ ...c, question: '' })); }}
            onKeyDown={event => { if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) start(); }} />
          <div className="field-foot">{errors.question ? <p className="field-error" id="question-error">{errors.question}</p> : <span />}<span className="counter">{question.length.toLocaleString()} / {(contract?.limits.question_characters ?? 2000).toLocaleString()}</span></div>
        </section>

        <section className="field-block" aria-labelledby="inputs-title">
          <div className="field-title-row"><h2 className="field-title" id="inputs-title">Inputs</h2>{picked.length > 0 && <span className="muted-text">{picked.length} files · {kilobytes(totalBytes)}</span>}</div>
          <div ref={inputsRef} tabIndex={-1} className="inputs-area" aria-describedby={errors.inputs ? 'inputs-error' : undefined}>
            {reuse ? <div className="reuse"><Icon name="rerun" /><div><strong>Reusing the inputs of “{runTitle({ title: reuse.overview?.title, question: reuse.request?.question ?? '' })}”</strong>
              <span>{reuse.inputs ? `${reuse.inputs.papers.length} paper${reuse.inputs.papers.length === 1 ? '' : 's'} · ${reuse.inputs.code_files.length} code files` : 'Saved inputs'}, exactly as they were investigated.</span></div>
              <button type="button" className="btn btn-quiet" onClick={() => setParam('from', '')} disabled={disabled}>Use different inputs</button></div>
            : example ? <div className="reuse"><Icon name="book" /><div><strong>Example: {example.title}</strong>
              <span>{example.files.map(file => `${file.role === 'paper' ? 'Paper' : 'Code'} ${file.name}`).join(' · ')}</span></div>
              <button type="button" className="btn btn-quiet" onClick={() => setParam('example', '')} disabled={disabled}>Use my own files</button></div>
            : <>
              <DropArea onFiles={add} disabled={disabled} />
              {picked.length > 0 && <ul className="picked">{picked.map((item, index) => <li key={item.file.name + item.file.size}>
                <Icon name={item.role === 'paper' ? 'file' : 'box'} /><span className="file-name" title={item.file.name}>{item.file.name}</span><span className="file-meta">{kilobytes(item.file.size)}</span>
                <label className="visually-hidden" htmlFor={`role-${index}`}>Role of {item.file.name}</label>
                <select id={`role-${index}`} value={item.role} disabled={disabled} onChange={event => setPicked(current => current.map((entry, at) => at === index ? { ...entry, role: event.target.value as Role } : entry))}>
                  <option value="paper">Paper</option><option value="code">Code</option></select>
                <button type="button" className="icon-btn" onClick={() => setPicked(current => current.filter((_, at) => at !== index))} aria-label={`Remove ${item.file.name}`} disabled={disabled}><Icon name="close" size={14} /></button>
              </li>)}</ul>}
              <button type="button" className="link-button" aria-expanded={showLinks || Boolean(paperUrl || codeUrl)} onClick={() => setShowLinks(value => !value)}>
                <Icon name="link" size={14} /> Add from a link instead (arXiv, OpenReview, GitHub)</button>
              {(showLinks || paperUrl || codeUrl) && <div className="link-fields">
                <label htmlFor="composer-paper-url"><span>Paper link</span><input id="composer-paper-url" type="url" inputMode="url" autoComplete="off" spellCheck={false} value={paperUrl} disabled={disabled}
                  placeholder="https://arxiv.org/abs/…" onChange={event => setPaperUrl(event.target.value)} /></label>
                <label htmlFor="composer-code-url"><span>Code link</span><input id="composer-code-url" type="url" inputMode="url" autoComplete="off" spellCheck={false} value={codeUrl} disabled={disabled}
                  placeholder="https://github.com/owner/repo" onChange={event => setCodeUrl(event.target.value)} /></label>
              </div>}
            </>}
          </div>
          {errors.inputs && <p className="field-error" id="inputs-error">{errors.inputs}</p>}
          {!reuse && exampleCards.length > 0 && <div className="examples" role="group" aria-label="Examples">
            <p className="field-help">Or start from an example</p>
            <div className="example-grid">{exampleCards.map(item => <button type="button" key={item.id} className="example" aria-pressed={example?.id === item.id} onClick={() => chooseExample(item)} disabled={disabled}>
              <strong>{item.title}</strong><span>{item.description}</span></button>)}</div>
          </div>}
        </section>

        <section className="field-block" aria-labelledby="options-title">
          <h2 className="field-title" id="options-title">Options</h2>
          <fieldset className="choice-group" disabled={disabled}><legend className="field-help">Output allowance per Nemotron request</legend>
            {(contract?.output_allowances ?? [8192, 16384, 32768]).map(value => <label key={value} className={`choice ${allowance === value ? 'selected' : ''}`}>
              <input type="radio" name="allowance" value={value} checked={allowance === value} onChange={() => setAllowance(value)} />
              <span><strong>{value.toLocaleString()} tokens</strong><small>{ALLOWANCES[value] ?? ''}</small></span></label>)}
          </fieldset>
          <label className="switch-row"><input type="checkbox" role="switch" checked={followUp} disabled={disabled} onChange={event => setFollowUp(event.target.checked)} />
            <span><strong>Design one follow-up experiment</strong><small>After the first result, Nemotron designs a second experiment from CounterLab’s measured summary.</small></span></label>
        </section>

        <section className="field-block start-block">
          <label className="consent2"><input ref={consentRef} type="checkbox" checked={consent} disabled={disabled} aria-invalid={Boolean(errors.consent)}
            onChange={event => { setConsent(event.target.checked); if (errors.consent) setErrors(c => ({ ...c, consent: '' })); }} />
            <span>I approve using my Nebius credits for this investigation: at most {contract?.limits.maximum_model_calls ?? 7} Nemotron requests of up to {allowance.toLocaleString()} output tokens each. Temporary Nebius errors are retried automatically, at most {Math.max(0, (contract?.retry_policy?.attempts ?? 4) - 1)} times per request. Uploaded code runs only inside the sandbox.</span></label>
          {errors.consent && <p className="field-error">{errors.consent}</p>}
          {formProblem && <p className="field-error" role="alert">{formProblem}</p>}
          {startError && <div className="alert alert-bad" role="alert"><Icon name="alert" /><div>{startError}{/Settings|key|sandbox/i.test(startError) && <div className="alert-actions"><AppLink route="settings" className="btn btn-secondary">Open Settings</AppLink></div>}</div></div>}
          <div className="start-row">
            <button type="submit" className="btn btn-primary btn-large" disabled={disabled || Boolean(running) || Boolean(notReady)} aria-describedby={notReady ? 'not-ready' : undefined}>
              {starting ? <>Uploading and starting…</> : <><Icon name="play" /> Start investigation</>}</button>
            <span className="muted-text"><Kbd>Ctrl</Kbd> <Kbd>Enter</Kbd> from the question</span>
          </div>
          {notReady && <p className="field-help" id="not-ready">{notReady === 'key' ? 'Connect Nemotron in Settings to start.' : 'Set up the sandbox in Settings to start.'}</p>}
        </section>
      </form>

      <aside className="composer-side" aria-label="Before you start">
        <Readiness />
        <section className="side-card">
          <h2 className="side-title">What happens next</h2>
          <ol className="how">
            <li><strong>Read</strong><span>Your files are unpacked and read as data. Nothing runs yet.</span></li>
            <li><strong>Design and commit</strong><span>{contract?.model?.replace('nvidia/', '') ?? 'Nemotron'} names competing explanations, what each predicts, and its bet. The plan is hashed before anything runs.</span></li>
            <li><strong>Check</strong><span>A deterministic guard rejects plans that can’t tell the explanations apart, ignore your code, or reach for the network.</span></li>
            <li><strong>Run twice</strong><span>Your code runs in a sealed container with paired seeds. The repeat must match exactly.</span></li>
            <li><strong>Report</strong><span>CounterLab writes the finding from the measurements and seals a replay package.</span></li>
          </ol>
          <p className="small-text">Typically 3–5 Nemotron requests and a few minutes. You can stop at any time.</p>
        </section>
      </aside>
    </div>
  </div>;
}

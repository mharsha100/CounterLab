import { useEffect, useRef, useState, type FormEvent } from 'react';
import { isEvidenceBuild, sourceBuildHref } from '../access';
import { failureMessage } from '../format';
import { useParam } from '../navigation';
import { action, api, canWrite, refreshLab, toast, useLab, when, type ConnectionCheck, type SandboxState } from './data';
import { Badge, Dialog, Icon, Spinner } from './ui';

function ConnectionStatus({ keyed, check, checking }: { keyed: boolean; check: ConnectionCheck | null | undefined; checking: boolean }) {
  if (checking) return <p className="status-line"><Spinner /> Checking the connection…</p>;
  if (!keyed) return <p className="status-line"><span className="status-dot2 bad" aria-hidden="true" /> Not connected. Add your Nebius API key below.</p>;
  if (!check) return <p className="status-line"><span className="status-dot2 neutral" aria-hidden="true" /> Key saved. Check the connection to confirm Nemotron is available.</p>;
  if (!check.ok) return <p className="status-line"><span className="status-dot2 bad" aria-hidden="true" /> Connection failed: {failureMessage(check.error ?? 'provider_error')}</p>;
  return <p className="status-line"><span className="status-dot2 good" aria-hidden="true" /> Connected to Nebius Token Factory. <strong>{check.model}</strong> is available
    <span className="muted-text"> · checked {when(check.checked_at)}{check.latency_ms !== undefined ? ` · ${check.latency_ms} ms` : ''}</span></p>;
}

function SandboxSection({ sandbox, writable }: { sandbox: SandboxState; writable: boolean }) {
  const [minimal, setMinimal] = useState(false);
  const [state, setState] = useState(sandbox);
  const building = state.setup?.state === 'building';
  useEffect(() => setState(sandbox), [sandbox]);
  useEffect(() => {
    if (!building) return;
    const timer = setInterval(async () => {
      try {
        const next = await api<SandboxState>('/api/sandbox');
        setState(next);
        if (next.setup?.state !== 'building') {
          refreshLab();
          toast(next.setup?.state === 'ready' ? 'Sandbox ready. Your code will run with no network access.' : next.setup?.message ?? 'The sandbox build failed.', next.setup?.state === 'ready' ? 'good' : 'bad');
        }
      } catch { /* keep polling */ }
    }, 2000);
    return () => clearInterval(timer);
  }, [building]);
  async function setup() {
    try { const result = await action<{ setup: SandboxState['setup'] }>('/api/sandbox/setup', 'setup-sandbox', { minimal }); setState(current => ({ ...current, setup: result.setup })); }
    catch (cause) { toast(cause instanceof Error ? cause.message : 'The sandbox build could not start.', 'bad'); }
  }
  return <section className="settings-section" id="sandbox" aria-labelledby="sandbox-title">
    <div className="settings-head"><h2 id="sandbox-title">Sandbox</h2>{state.ready ? <Badge tone="good" dot>Ready</Badge> : building ? <Badge tone="run" dot>Setting up</Badge> : <Badge tone="bad" dot>Not set up</Badge>}</div>
    <p className="settings-sub">Uploaded code and the experiment code Nemotron writes run only here: a Docker container with no network, a read-only system, a non-root user and CPU, memory and time limits.</p>
    {state.ready ? <dl className="kv">
      <div><dt>Isolation</dt><dd>{state.isolation === 'docker_no_network' ? 'Docker · no network · non-root · read-only' : 'Local process (no network isolation)'}</dd></div>
      {state.image_id && <div><dt>Image</dt><dd><code>{state.image_id.slice(0, 19)}…</code></dd></div>}
      {state.packages && <div><dt>Python packages</dt><dd>{Object.entries(state.packages).map(([name, version]) => `${name} ${version}`).join(', ') || 'Standard library only'}</dd></div>}
    </dl> : <>
      {building ? <p className="status-line"><Spinner /> {state.setup?.message ?? 'Building'}… This downloads Python packages once and can take a few minutes.</p>
        : <p className="status-line"><span className="status-dot2 bad" aria-hidden="true" /> {state.setup?.state === 'failed' ? state.setup.message : 'The sandbox image has not been built on this computer yet.'}</p>}
      {state.setup?.state === 'failed' && state.setup.detail && <details className="disclosure"><summary>Build output</summary><pre tabIndex={0}>{state.setup.detail}</pre></details>}
      {writable && <div className="form-row">
        <button type="button" className="btn btn-primary" onClick={setup} disabled={building}><Icon name="box" /> {building ? 'Setting up…' : 'Set up sandbox'}</button>
        <label className="inline-check"><input type="checkbox" checked={minimal} onChange={event => setMinimal(event.target.checked)} disabled={building} /> Minimal build (standard library only, works offline)</label>
      </div>}
      <p className="small-text">Docker Desktop must be running. From a terminal you can also run <code>python scripts/setup_open_runner.py</code>.</p>
    </>}
  </section>;
}

export default function Settings() {
  const { contract } = useLab();
  const tab = useParam('tab');
  const [key, setKey] = useState('');
  const [replacing, setReplacing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [checking, setChecking] = useState(false);
  const [probing, setProbing] = useState(false);
  const [confirmProbe, setConfirmProbe] = useState(false);
  const [confirmRemove, setConfirmRemove] = useState(false);
  const [keyError, setKeyError] = useState('');
  const [model, setModel] = useState('');
  const keyInput = useRef<HTMLInputElement>(null);
  useEffect(() => { if (tab === 'sandbox') requestAnimationFrame(() => document.getElementById('sandbox')?.scrollIntoView({ block: 'start' })); }, [tab, Boolean(contract)]);
  useEffect(() => { if (contract) setModel(contract.model); }, [contract?.model]);

  if (isEvidenceBuild || contract?.read_only) return <div className="page settings-page">
    <header className="page-head"><div><h1 className="page-title" tabIndex={-1}>Settings</h1>
      <p className="page-sub">{isEvidenceBuild ? 'The hosted demo has no model connection or sandbox.' : 'Read-only mode: settings cannot be changed.'}</p></div></header>
    <section className="settings-section"><h2>Run CounterLab yourself</h2>
      <p className="settings-sub">Download the source, add your Nebius API key in Settings, set up the sandbox and investigate any paper or code with NVIDIA Nemotron.</p>
      {isEvidenceBuild && <a className="btn btn-primary" href={sourceBuildHref()}><Icon name="download" /> Download CounterLab</a>}</section>
  </div>;

  const connection = contract?.connection;
  const keyed = Boolean(connection?.key_configured);
  const check = connection?.last_check;
  const writable = canWrite(contract);

  async function saveKey(event: FormEvent) {
    event.preventDefault();
    if (!key.trim()) { setKeyError('Paste your Nebius API key.'); keyInput.current?.focus(); return; }
    setSaving(true); setKeyError('');
    try {
      const result = await action<{ check: ConnectionCheck | null }>('/api/settings/api-key', 'save-settings', { api_key: key });
      setKey(''); setReplacing(false); await refreshLab();
      toast(result.check?.ok ? 'Key saved. Nemotron is connected.' : 'Key saved, but the connection check failed. See the status above.', result.check?.ok ? 'good' : 'bad');
    } catch (cause) { setKeyError(cause instanceof Error ? cause.message : 'The key could not be saved.'); keyInput.current?.focus(); }
    finally { setSaving(false); }
  }
  async function removeKey() {
    try { await action('/api/settings/api-key/remove', 'save-settings'); await refreshLab(); toast('Key removed from this computer.', 'good'); }
    catch (cause) { toast(cause instanceof Error ? cause.message : 'The key could not be removed.', 'bad'); }
    finally { setConfirmRemove(false); }
  }
  async function runCheck() {
    setChecking(true);
    try { const result = await action<ConnectionCheck>('/api/connection/check', 'check-connection'); await refreshLab();
      toast(result.ok ? `Connected. ${result.model} is available.` : failureMessage(result.error ?? 'provider_error'), result.ok ? 'good' : 'bad'); }
    catch (cause) { toast(cause instanceof Error ? cause.message : 'The connection could not be checked.', 'bad'); }
    finally { setChecking(false); }
  }
  async function runProbe() {
    setConfirmProbe(false); setProbing(true);
    try { const result = await action<ConnectionCheck>('/api/connection/probe', 'check-connection', { confirm_credit_use: true }); await refreshLab();
      const probe = result.probe;
      toast(probe?.ok ? `Nemotron replied in ${((probe.latency_ms ?? 0) / 1000).toFixed(1)} s with valid JSON.` : failureMessage(probe?.error ?? result.error ?? 'provider_error'), probe?.ok ? 'good' : 'bad'); }
    catch (cause) { toast(cause instanceof Error ? cause.message : 'The test request failed.', 'bad'); }
    finally { setProbing(false); }
  }
  async function saveModel() {
    try { await action('/api/settings/model', 'save-settings', { model }); await refreshLab(); toast(`New investigations will use ${model}.`, 'good'); }
    catch (cause) { toast(cause instanceof Error ? cause.message : 'The model could not be saved.', 'bad'); }
  }
  const models = Array.from(new Set([...(check?.nemotron_models ?? []), contract?.model ?? ''].filter(Boolean)));
  const probe = check?.probe;

  return <div className="page settings-page">
    <header className="page-head"><div><h1 className="page-title" tabIndex={-1}>Settings</h1><p className="page-sub">Connect NVIDIA Nemotron and prepare the sandbox. Both stay on this computer.</p></div></header>

    <section className="settings-section" aria-labelledby="connection-title">
      <div className="settings-head"><h2 id="connection-title">Nemotron connection</h2>{keyed && check?.ok ? <Badge tone="good" dot>Connected</Badge> : keyed ? <Badge tone={check ? 'bad' : 'neutral'} dot>{check ? 'Problem' : 'Not checked'}</Badge> : <Badge tone="bad" dot>Not connected</Badge>}</div>
      <p className="settings-sub">CounterLab calls NVIDIA Nemotron through Nebius Token Factory. Temporary errors (rate limits, server errors, dropped connections) are retried automatically with backoff; every retry is recorded.</p>
      <ConnectionStatus keyed={keyed} check={check} checking={checking} />
      {check?.ok && check.model_note === 'preferred_model_unavailable' && <p className="note"><Icon name="alert" /> {check.preferred_model} is not in your catalog, so CounterLab uses {check.model}.</p>}

      <h3 className="settings-label">API key</h3>
      {keyed && !replacing ? <div className="form-row"><span className="key-saved"><Icon name="key" /> A key is saved in this computer’s <code>.env</code> file. It is never shown again.</span>
        {writable && <><button type="button" className="btn btn-secondary" onClick={() => { setReplacing(true); requestAnimationFrame(() => keyInput.current?.focus()); }}>Replace key</button>
          <button type="button" className="btn btn-quiet danger" onClick={() => setConfirmRemove(true)}>Remove</button></>}</div>
        : <form className="key-form" onSubmit={saveKey} noValidate>
          <label htmlFor="nebius-key" className="visually-hidden">Nebius API key</label>
          <input ref={keyInput} id="nebius-key" name="counterlab-nebius-key" type="password" autoComplete="off" spellCheck={false} data-1p-ignore data-lpignore="true"
            placeholder="Paste your Nebius Token Factory API key…" value={key} onChange={event => { setKey(event.target.value); setKeyError(''); }} disabled={!writable || saving}
            aria-invalid={Boolean(keyError)} aria-describedby={keyError ? 'key-error key-help' : 'key-help'} />
          <button type="submit" className="btn btn-primary" disabled={!writable || saving}>{saving ? 'Saving and checking…' : 'Save and connect'}</button>
          {replacing && <button type="button" className="btn btn-quiet" onClick={() => { setReplacing(false); setKey(''); setKeyError(''); }}>Cancel</button>}
          {keyError && <p className="field-error" id="key-error">{keyError}</p>}
          <p className="field-help" id="key-help">Create a key at <a href="https://tokenfactory.nebius.com/" target="_blank" rel="noreferrer">tokenfactory.nebius.com <Icon name="external" size={12} /></a>. It is saved to the <code>.env</code> file in your CounterLab folder and only the local backend reads it.</p>
        </form>}

      {keyed && <div className="form-row checks-row">
        <button type="button" className="btn btn-secondary" onClick={runCheck} disabled={checking || !writable}><Icon name="activity" /> {checking ? 'Checking…' : 'Check connection'}</button>
        <span className="small-text">Reads the model catalog. No tokens used.</span>
      </div>}

      {keyed && check?.ok && <>
        <h3 className="settings-label">Model</h3>
        <div className="form-row">
          <label htmlFor="model-select" className="visually-hidden">Nemotron model</label>
          <select id="model-select" value={model} onChange={event => setModel(event.target.value)} disabled={!writable}>
            {models.map(item => <option key={item} value={item}>{item}{item === contract?.default_model ? ' (recommended)' : ''}</option>)}</select>
          <button type="button" className="btn btn-secondary" onClick={saveModel} disabled={!writable || model === contract?.model}>Use this model</button>
        </div>
        <h3 className="settings-label">End-to-end test</h3>
        <div className="form-row">
          <button type="button" className="btn btn-secondary" onClick={() => setConfirmProbe(true)} disabled={probing || !writable}><Icon name="bolt" /> {probing ? 'Waiting for Nemotron…' : 'Send a test request'}</button>
          {probe && <span className={`probe-result ${probe.ok ? 'ok' : 'no'}`}>{probe.ok ? <><Icon name="check" /> Replied in {((probe.latency_ms ?? 0) / 1000).toFixed(1)} s · {probe.schema_mode === 'strict' ? 'strict JSON schema' : `${probe.schema_mode?.replace('_', ' ')} output`} · {probe.usage?.total_tokens ?? '—'} tokens</>
            : <><Icon name="alert" /> {failureMessage(probe.error ?? 'provider_error')}</>}<span className="muted-text"> · {when(probe.checked_at)}</span></span>}
        </div>
      </>}
    </section>

    {contract && <SandboxSection sandbox={contract.sandbox} writable={writable} />}

    <section className="settings-section" aria-labelledby="privacy-title">
      <h2 id="privacy-title">How your data is handled</h2>
      <ul className="check-list">
        <li><Icon name="check" /> Your API key stays in the local <code>.env</code> file. It is never sent to the browser, the sandbox, logs or exports.</li>
        <li><Icon name="check" /> Papers and code go to Nemotron as data; instructions inside them are not followed.</li>
        <li><Icon name="check" /> Code runs only in the sandbox, with no network and no access to your files.</li>
        <li><Icon name="check" /> Each investigation makes at most {contract?.limits.maximum_model_calls ?? 7} Nemotron requests. Retries are bounded and recorded.</li>
      </ul>
    </section>

    <Dialog open={confirmProbe} onClose={() => setConfirmProbe(false)} title="Send a test request?" size="s"
      footer={<><button type="button" className="btn btn-secondary" onClick={() => setConfirmProbe(false)}>Cancel</button><button type="button" className="btn btn-primary" onClick={runProbe}>Send test request</button></>}>
      <p>CounterLab sends one short structured request to {check?.model ?? 'Nemotron'} to confirm the key, the model and JSON output work together. It uses roughly 100 to 2,000 tokens of your Nebius credit.</p>
    </Dialog>
    <Dialog open={confirmRemove} onClose={() => setConfirmRemove(false)} title="Remove the API key?" size="s"
      footer={<><button type="button" className="btn btn-secondary" onClick={() => setConfirmRemove(false)}>Cancel</button><button type="button" className="btn btn-danger" onClick={removeKey}>Remove key</button></>}>
      <p>New investigations can’t start until you add a key again. Finished investigations are not affected.</p>
    </Dialog>
  </div>;
}

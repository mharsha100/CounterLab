import { useEffect, useMemo, useRef, useState, type KeyboardEvent as ReactKeyboardEvent, type ReactNode } from 'react';
import { isEvidenceBuild, sourceBuildHref } from './access';
import { hrefFor, linkClick, navigateTo, useParam, useRoute } from './navigation';
import { caseViews, routes, type Route, type View } from './navigationProtocol';
import PagingCase from './PagingCase';
import Composer from './lab/Composer';
import Home from './lab/Home';
import RunPage from './lab/RunPage';
import Runs from './lab/Runs';
import Settings from './lab/Settings';
import { action, active, canWrite, refreshLab, runTitle, useLab } from './lab/data';
import { BrandMark, Dialog, Icon, Kbd, Toaster, type IconName } from './lab/ui';

const PRIMARY: { route: Route; label: string; icon: IconName; views: View[] }[] = [
  { route: 'home', label: 'Home', icon: 'home', views: ['home'] },
  { route: 'runs', label: 'Investigations', icon: 'list', views: ['runs', 'run'] },
];
const CASE: { route: Route; label: string }[] = [
  { route: 'demo', label: 'Guided tour' }, { route: 'investigation', label: 'Investigation' }, { route: 'sources', label: 'Sources' },
  { route: 'research', label: 'Research study' }, { route: 'evaluation', label: 'Evaluation' }, { route: 'evidence', label: 'Evidence' },
  { route: 'history', label: 'Run history' },
];

function ConnectionPill() {
  const { contract } = useLab();
  if (!contract) return <span className="pill"><span className="status-dot2 neutral" aria-hidden="true" /><span className="pill-text">Loading</span></span>;
  if (isEvidenceBuild) return <span className="pill" title="This hosted demo makes no model calls"><span className="status-dot2 neutral" aria-hidden="true" /><span className="pill-text">Hosted demo</span></span>;
  if (contract.read_only) return <span className="pill"><span className="status-dot2 neutral" aria-hidden="true" /><span className="pill-text">Read-only</span></span>;
  const keyed = contract.connection?.key_configured, check = contract.connection?.last_check;
  const tone = !keyed ? 'bad' : check && !check.ok ? 'bad' : check?.ok ? 'good' : 'neutral';
  const text = !keyed ? 'Nemotron not connected' : check && !check.ok ? 'Nemotron unreachable' : check?.ok ? 'Nemotron connected' : 'Nemotron key saved';
  return <a className="pill pill-link" href={hrefFor('settings')} onClick={linkClick('settings')} title={check?.ok ? `${check.model} via Nebius Token Factory` : 'Open Settings'}>
    <span className={`status-dot2 ${tone}`} aria-hidden="true" /><span className="pill-text">{text}</span></a>;
}

interface Command { id: string; label: string; hint?: string; icon: IconName; run: () => void }
function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { contract, items } = useLab();
  const [query, setQuery] = useState('');
  const [index, setIndex] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => { if (open) { setQuery(''); setIndex(0); } }, [open]);
  const commands = useMemo<Command[]>(() => {
    const go = (route: Route, params = {}) => () => { navigateTo(route, params); onClose(); };
    const list: Command[] = [];
    if (canWrite(contract)) list.push({ id: 'new', label: 'New investigation', hint: 'N', icon: 'plus', run: go('lab') });
    list.push({ id: 'home', label: 'Go to Home', icon: 'home', run: go('home') }, { id: 'runs', label: 'Go to Investigations', icon: 'list', run: go('runs') },
      { id: 'settings', label: 'Open Settings', icon: 'sliders', run: go('settings') }, { id: 'case', label: 'Open the paging case study', icon: 'book', run: go('demo') });
    if (canWrite(contract)) for (const example of contract?.examples ?? []) list.push({ id: `example-${example.id}`, label: `Start example: ${example.title}`, icon: 'play', run: go('lab', { example: example.id }) });
    for (const item of items.slice(0, 20)) list.push({ id: `run-${item.id}`, label: runTitle(item), hint: item.state.replaceAll('_', ' '), icon: active(item.state) ? 'activity' : 'file', run: go('run', { id: item.id }) });
    return list;
  }, [contract, items, onClose]);
  const shown = commands.filter(command => command.label.toLowerCase().includes(query.trim().toLowerCase())).slice(0, 12);
  function keys(event: ReactKeyboardEvent) {
    if (event.key === 'ArrowDown') { event.preventDefault(); setIndex(value => Math.min(value + 1, shown.length - 1)); }
    if (event.key === 'ArrowUp') { event.preventDefault(); setIndex(value => Math.max(value - 1, 0)); }
    if (event.key === 'Enter' && shown[index]) { event.preventDefault(); shown[index].run(); }
  }
  return <Dialog open={open} onClose={onClose} title="Go to" size="m">
    <div className="palette" onKeyDown={keys}>
      <div className="search"><Icon name="search" /><input ref={input} data-autofocus type="text" role="combobox" aria-expanded="true" aria-controls="palette-list" aria-label="Search commands and investigations"
        aria-activedescendant={shown[index] ? `cmd-${shown[index].id}` : undefined} placeholder="Search investigations, examples and pages…" value={query}
        onChange={event => { setQuery(event.target.value); setIndex(0); }} autoComplete="off" spellCheck={false} /></div>
      <ul id="palette-list" role="listbox" aria-label="Results">{shown.map((command, position) => <li key={command.id} id={`cmd-${command.id}`} role="option" aria-selected={position === index}
        className={position === index ? 'active' : ''} onMouseEnter={() => setIndex(position)} onClick={command.run}>
        <Icon name={command.icon} /><span>{command.label}</span>{command.hint && <span className="muted-text">{command.hint}</span>}</li>)}
        {!shown.length && <li className="muted-text" role="option" aria-selected="false" aria-disabled="true">No matches</li>}</ul>
    </div>
  </Dialog>;
}

function Sidebar({ view, open, onNavigate }: { view: View; open: boolean; onNavigate: () => void }) {
  const { contract, items } = useLab();
  const running = items.filter(item => active(item.state)).length;
  const inCase = caseViews.includes(view);
  const [caseOpen, setCaseOpen] = useState(inCase);
  useEffect(() => { if (inCase) setCaseOpen(true); }, [inCase]);
  const link = (route: Route, label: string, icon: IconName | null, selected: boolean, extra?: ReactNode) =>
    <a key={route} href={hrefFor(route)} onClick={event => { linkClick(route)(event); onNavigate(); }} className={`side-link ${selected ? 'selected' : ''}`} aria-current={selected ? 'page' : undefined}>
      {icon && <Icon name={icon} />}<span>{label}</span>{extra}</a>;
  return <aside className={`side ${open ? 'open' : ''}`} aria-label="CounterLab">
    <a className="side-brand" href={hrefFor('home')} onClick={event => { linkClick('home')(event); onNavigate(); }}><BrandMark /><span>CounterLab</span></a>
    {canWrite(contract) ? <a className="side-new" href={hrefFor('lab')} onClick={event => { linkClick('lab')(event); onNavigate(); }} aria-current={view === 'lab' ? 'page' : undefined}>
      <Icon name="plus" /><span>New investigation</span><Kbd>N</Kbd></a>
      : isEvidenceBuild ? <a className="side-new" href={sourceBuildHref()}><Icon name="download" /><span>Download CounterLab</span></a> : null}
    <nav aria-label="Main" className="side-nav">
      {PRIMARY.map(item => link(item.route, item.label, item.icon, item.views.includes(view),
        item.route === 'runs' && running ? <span className="side-count run" title={`${running} running`}>{running}</span> : item.route === 'runs' && items.length ? <span className="side-count">{items.length}</span> : null))}
    </nav>
    <div className="side-group">
      <button type="button" className="side-group-toggle" aria-expanded={caseOpen} aria-controls="case-nav" onClick={() => setCaseOpen(value => !value)}>
        <Icon name="book" /><span>Case study</span><Icon name={caseOpen ? 'chevronDown' : 'chevron'} size={14} className="toggle-icon" /></button>
      {caseOpen && <nav id="case-nav" aria-label="Case study" className="side-nav nested">{CASE.map(item => link(item.route, item.label, null, routes[item.route].view === view))}</nav>}
    </div>
    <div className="side-bottom">
      <nav aria-label="Settings" className="side-nav">{link('settings', 'Settings', 'sliders', view === 'settings')}</nav>
      <div className="side-powered"><span>Powered by</span><strong>NVIDIA Nemotron</strong><span>on Nebius Token Factory</span></div>
    </div>
  </aside>;
}

export default function App() {
  const route = useRoute();
  const view = routes[route].view;
  const id = useParam('id');
  const { contract, items, error, loaded } = useLab();
  const [menu, setMenu] = useState(false);
  const [palette, setPalette] = useState(false);
  const checked = useRef(false);
  const previous = useRef(route);
  const anyActive = items.some(item => active(item.state)) || Boolean(contract?.active_id);

  useEffect(() => { refreshLab(); }, []);
  useEffect(() => {
    if (isEvidenceBuild) return;
    const timer = setInterval(() => { if (document.visibilityState === 'visible') refreshLab(); }, anyActive ? 2500 : 20000);
    const focus = () => refreshLab();
    window.addEventListener('focus', focus);
    return () => { clearInterval(timer); window.removeEventListener('focus', focus); };
  }, [anyActive]);
  useEffect(() => {
    // One free catalog check per session, so the connection status is real rather than assumed.
    if (checked.current || !contract || !canWrite(contract) || !contract.connection?.key_configured || contract.connection.last_check) return;
    checked.current = true;
    action('/api/connection/check', 'check-connection').then(() => refreshLab()).catch(() => refreshLab());
  }, [contract]);
  useEffect(() => {
    document.title = `${routes[route].label} — CounterLab`;
    if (previous.current !== route) {
      previous.current = route;
      setMenu(false);
      requestAnimationFrame(() => (document.querySelector('#main-content h1') as HTMLElement | null)?.focus());
      window.scrollTo({ top: 0 });
    }
  }, [route, id]);
  useEffect(() => {
    function keys(event: KeyboardEvent) {
      const target = event.target as HTMLElement;
      const typing = ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName) || target.isContentEditable;
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); setPalette(true); return; }
      if (typing || event.metaKey || event.ctrlKey || event.altKey || document.querySelector('dialog[open]')) return;
      if (event.key === 'n' && canWrite(contract)) { event.preventDefault(); navigateTo('lab'); }
    }
    window.addEventListener('keydown', keys);
    return () => window.removeEventListener('keydown', keys);
  }, [contract]);

  const page = view === 'home' ? <Home /> : view === 'lab' ? <Composer /> : view === 'runs' ? <Runs />
    : view === 'run' ? (id ? <RunPage key={id} id={id} /> : <Runs />) : view === 'settings' ? <Settings /> : <PagingCase />;
  const crumb = caseViews.includes(view) ? 'Case study' : routes[route].label;

  return <div className="shell">
    <a className="skip-link" href="#main-content">Skip to main content</a>
    <Sidebar view={view} open={menu} onNavigate={() => setMenu(false)} />
    {menu && <button type="button" className="scrim" aria-label="Close menu" onClick={() => setMenu(false)} />}
    <div className="shell-main">
      <header className="top">
        <button type="button" className="icon-btn menu-btn" aria-label="Open menu" aria-expanded={menu} onClick={() => setMenu(true)}><Icon name="menu" /></button>
        <a className="top-brand" href={hrefFor('home')} onClick={linkClick('home')}><BrandMark size={24} /><span>CounterLab</span></a>
        <span className="top-crumb" aria-hidden="true">{crumb}</span>
        <button type="button" className="top-search" onClick={() => setPalette(true)} aria-keyshortcuts="Control+K Meta+K" aria-label="Search or jump to (Ctrl K)">
          <Icon name="search" /><span>Search or jump to…</span><Kbd>Ctrl K</Kbd></button>
        <ConnectionPill />
      </header>
      {error && !loaded && <div className="alert alert-bad page-alert" role="alert"><Icon name="alert" /><div><strong>CounterLab could not be reached.</strong> {error}
        <div className="alert-actions"><button type="button" className="btn btn-secondary" onClick={() => refreshLab()}>Try again</button></div></div></div>}
      <main id="main-content" tabIndex={-1} className="app-main">{page}</main>
    </div>
    <CommandPalette open={palette} onClose={() => setPalette(false)} />
    <Toaster />
  </div>;
}

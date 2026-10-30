import { useEffect, useId, useRef, type AnchorHTMLAttributes, type ReactNode } from 'react';
import { hrefFor, linkClick } from '../navigation';
import type { Route, ViewParam } from '../navigationProtocol';
import { dismissToast, stateLabel, stateTone, toast, useToasts } from './data';

const ICONS = {
  home: 'M3 10.5 12 3l9 7.5M5 9.5V21h5v-6h4v6h5V9.5',
  plus: 'M12 5v14M5 12h14',
  list: 'M9 6h12M9 12h12M9 18h12M4 6h.01M4 12h.01M4 18h.01',
  sliders: 'M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6',
  search: 'm20 20-4.2-4.2M10.5 17.5a7 7 0 1 1 0-14 7 7 0 0 1 0 14Z',
  book: 'M3 5c4-2 6-1 9 1 3-2 5-3 9-1v15c-4-2-6-1-9 1-3-2-5-3-9-1V5Zm9 1v15',
  play: 'm8 5 11 7-11 7V5Z',
  check: 'm5 12 4.5 4.5L19 7',
  close: 'm6 6 12 12M6 18 18 6',
  download: 'M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4',
  upload: 'M12 16V4m-5 5 5-5 5 5M4 16v5h16v-5',
  external: 'M14 3h7v7m0-7L10 14M10 4H4v16h16v-6',
  chevron: 'm9 5 7 7-7 7',
  chevronDown: 'm5 9 7 7 7-7',
  arrow: 'M5 12h14m-5-5 5 5-5 5',
  back: 'M19 12H5m5-5-5 5 5 5',
  activity: 'M3 12h4l3-8 4 16 3-8h4',
  history: 'M3 10a9 9 0 1 1 1 7M3 4v6h6m3-3v6l4 2',
  file: 'M14 3H5v18h14V8l-5-5Zm0 0v5h5M8 12h8m-8 4h6',
  stop: 'M7 7h10v10H7z',
  rerun: 'M20 12a8 8 0 1 1-2.3-5.6L20 8.7M20 3.5v5.2h-5.2',
  copy: 'M9 9h11v11H9zM5 15H4V4h11v1',
  alert: 'M12 9v4m0 4h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z',
  box: 'M21 8 12 3 3 8v8l9 5 9-5V8ZM3 8l9 5 9-5M12 13v8',
  key: 'M14.5 4a5.5 5.5 0 1 1-5.2 7.3L3 17.6V21h3.4v-2.2h2.2v-2.2h2.2l1.5-1.5A5.5 5.5 0 0 1 14.5 4Zm2 3.5h.01',
  menu: 'M4 6h16M4 12h16M4 18h16',
  archive: 'M3 4h18v4H3zM5 8v12h14V8M10 12h4',
  bolt: 'M13 2 4 14h7l-1 8 9-12h-7l1-8Z',
  shield: 'M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6l-8-3Z',
  link: 'M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1',
  dot: 'M12 12h.01',
} as const;
export type IconName = keyof typeof ICONS;

export function Icon({ name, size = 16, className }: { name: IconName; size?: number; className?: string }) {
  return <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75"
    strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false"><path d={ICONS[name]} /></svg>;
}

export function BrandMark({ size = 28 }: { size?: number }) {
  return <span className="brand-glyph" style={{ width: size, height: size }} aria-hidden="true">
    <svg width={size * 0.64} height={size * 0.64} viewBox="0 0 40 40" fill="none"><path d="M8 14h23l-6-6M32 26H9l6 6" stroke="currentColor" strokeWidth="3.4" strokeLinecap="round" strokeLinejoin="round" /></svg>
  </span>;
}

export type Tone = 'good' | 'bad' | 'warn' | 'run' | 'neutral' | 'brand';
export function Badge({ tone = 'neutral', children, dot = false, title }: { tone?: Tone; children: ReactNode; dot?: boolean; title?: string }) {
  return <span className={`badge2 badge2-${tone}`} title={title}>{dot && <span className="badge2-dot" aria-hidden="true" />}{children}</span>;
}
export function StateBadge({ state }: { state: string }) {
  return <Badge tone={stateTone(state)} dot>{stateLabel(state)}</Badge>;
}
export function BetBadge({ outcome, experiment }: { outcome: string; experiment?: number }) {
  const tone = outcome === 'held' ? 'good' : outcome === 'failed' ? 'bad' : 'neutral';
  const mark = outcome === 'held' ? '✓' : outcome === 'failed' ? '✗' : '–';
  return <Badge tone={tone} title={experiment ? `Experiment ${experiment}: Nemotron’s committed bet ${outcome}` : undefined}>
    {mark} {experiment ? `Bet ${experiment} ` : 'Bet '}{outcome}</Badge>;
}
export function Kbd({ children }: { children: ReactNode }) { return <kbd className="kbd">{children}</kbd>; }

export function AppLink({ route, params, children, ...rest }: { route: Route; params?: Partial<Record<ViewParam, string>>; children: ReactNode } & AnchorHTMLAttributes<HTMLAnchorElement>) {
  return <a href={hrefFor(route, params)} onClick={linkClick(route, params)} {...rest}>{children}</a>;
}

export function Empty({ icon = 'box', title, children, action }: { icon?: IconName; title: string; children?: ReactNode; action?: ReactNode }) {
  return <div className="empty2" role="status"><span className="empty2-icon"><Icon name={icon} size={20} /></span><h3>{title}</h3>{children && <p>{children}</p>}{action}</div>;
}
export function Skeleton({ lines = 3 }: { lines?: number }) {
  return <div className="skeleton" aria-hidden="true">{Array.from({ length: lines }, (_, index) => <span key={index} style={{ width: `${92 - index * 14}%` }} />)}</div>;
}
export function Spinner({ label }: { label?: string }) {
  return <span className="spin" role={label ? 'status' : undefined} aria-label={label} />;
}

export function Dialog({ open, onClose, title, children, footer, size = 'm' }: { open: boolean; onClose: () => void; title: string; children: ReactNode; footer?: ReactNode; size?: 's' | 'm' | 'l' }) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) { dialog.showModal(); (dialog.querySelector('[data-autofocus]') as HTMLElement | null)?.focus(); }
    if (!open && dialog.open) dialog.close();
  }, [open]);
  return <dialog ref={ref} className={`dialog2 dialog2-${size}`} aria-labelledby={titleId} onCancel={event => { event.preventDefault(); onClose(); }}
    onClick={event => { if (event.target === ref.current) onClose(); }}>
    <div className="dialog2-inner">
      <header><h2 id={titleId}>{title}</h2><button type="button" className="icon-btn" onClick={onClose} aria-label="Close"><Icon name="close" /></button></header>
      <div className="dialog2-body">{children}</div>
      {footer && <footer>{footer}</footer>}
    </div>
  </dialog>;
}

export function Toaster() {
  const items = useToasts();
  return <div className="toasts" role="region" aria-label="Notifications" aria-live="polite">
    {items.map(item => <div key={item.id} className={`toast2 toast2-${item.tone}`}>
      <Icon name={item.tone === 'good' ? 'check' : item.tone === 'bad' ? 'alert' : 'dot'} />
      <span>{item.text}</span>
      <button type="button" className="icon-btn" onClick={() => dismissToast(item.id)} aria-label="Dismiss"><Icon name="close" size={14} /></button>
    </div>)}
  </div>;
}

export async function copyText(text: string, done = 'Copied') {
  try { await navigator.clipboard.writeText(text); toast(done, 'good'); }
  catch { toast('Copy failed. Select the text and copy it manually.', 'bad'); }
}

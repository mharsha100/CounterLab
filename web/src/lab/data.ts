// Shared data for the product screens: types, API calls, a small store and the composer draft.
import { useSyncExternalStore } from 'react';
import { isEvidenceBuild, projectFetch } from '../access';

export type Role = 'paper' | 'code';
export interface Example { id: string; title: string; description: string; question: string; kind: string; files: { name: string; role: Role; bytes: number }[] }
export interface ConnectionCheck {
  ok: boolean; checked_at: string; latency_ms?: number; model?: string | null; model_note?: string | null; error?: string | null;
  preferred_model?: string; nemotron_models?: string[]; retries?: number;
  probe?: null | { ok: boolean; checked_at: string; latency_ms?: number; error?: string | null; schema_mode?: string; returned_model?: string | null;
    usage?: Record<string, number> };
}
export interface SandboxState {
  ready: boolean; mode: string; message?: string; isolation?: string; image_id?: string; packages?: Record<string, string>;
  setup?: { state: 'idle' | 'building' | 'ready' | 'failed'; message?: string; detail?: string; started_at?: string; finished_at?: string };
}
export interface Contract {
  read_only: boolean; model: string; default_model: string; provider: string; provider_mode: string; live_configured: boolean;
  connection?: { key_configured: boolean; preferred_model: string; last_check: ConnectionCheck | null };
  sandbox: SandboxState; active_id?: string | null;
  output_allowances: number[]; default_output_allowance: number; examples: Example[];
  retry_policy?: { attempts: number; retried: string };
  limits: { upload_megabytes: number; files: number; maximum_model_calls: number; measure_calls: number; sandbox_wall_seconds: number; question_characters: number };
}
export interface Bet { experiment: number; explanation: string; outcome: 'held' | 'failed' | 'inconclusive' | string }
export interface Overview {
  title: string | null; experiments: number; experiments_measured: number; bets: Bet[]; model_calls: number | null;
  tokens: number | null; automatic_retries?: number; model: string | null; duration_seconds: number | null;
}
export interface ListItem extends Overview {
  id: string; kind: 'recorded' | 'live'; created_at: string; state: string; question: string; provider_mode?: string; phase?: string; error?: string | null;
}
export interface Expected { metric: string; left: string; relation: 'greater' | 'less' | 'equal'; right: string; tolerance: number }
export interface Plan {
  title: string; question: string; factor: string; bet: string; seeds: number[]; implementation_note: string;
  claim: { statement: string; source: string; evidence_quote: string };
  explanations: { id: string; statement: string; expected: Expected[] }[];
  conditions: { id: string; label: string; description: string }[];
  metrics: { id: string; label: string; unit: string; description: string }[];
}
export interface Check { check: string; passed: boolean; message: string }
export interface Attempt { number: number; admission?: { accepted: boolean; checks: Check[] }; run?: { status: string; failed_calls: number; rows: number };
  repeat?: { status: string }; feedback?: { kind: string; failed_checks?: Check[]; examples?: { condition: string; seed: number; error: string }[]; traceback?: string; reason?: string };
  repair_summary?: string; repair_failed?: string }
export interface Stat { n: number; mean: number | null; std: number | null; min: number | null; max: number | null; per_seed: number[] }
export interface Verdict extends Expected { explanation: string; status: 'held' | 'failed' | 'inconclusive'; reason?: string; left_mean?: number; right_mean?: number;
  difference?: number; seeds_agreeing?: number; seeds_compared: number; sign_test_p?: number | null }
export interface Evaluation { complete: boolean; reproduced: boolean; stable_metrics: Record<string, boolean>; measurements: Record<string, Record<string, Stat>>;
  verdicts: Verdict[]; explanations: { id: string; statement: string; status: string }[]; bet: { explanation: string; outcome: string }; finding: string[];
  errors: { condition: string; seed: number; error: string }[] }
export interface Experiment { index: number; plan?: Plan; plan_sha256?: string; committed_at?: string; status?: string; reason?: string; attempts: Attempt[];
  sandbox?: { mode?: string; isolation?: string; packages?: Record<string, string>; image_id?: string }; evaluation?: Evaluation; harness_code?: string;
  run_status?: string; harness_output_tail?: string; runtime?: { python?: string; elapsed_seconds?: number } }
export interface CallEntry { purpose: string; outcome: string; elapsed_seconds?: number; usage?: Record<string, number>; returned_model?: string; finish_reason?: string; error?: string; max_tokens?: number }
export interface ProviderEvent { at: string; kind: string; purpose: string; attempt?: number; code?: string; delay_seconds?: number; status?: number; from?: string; to?: string }
export interface Run {
  id: string; kind: 'recorded' | 'live'; state: string; phase: string; notice?: string | null; step?: number; error: string | null; detail: string | null;
  created_at: string; provider_mode?: string; reused_from?: string | null;
  summary: null | { status: string; review_reason: string | null; model_calls: number; maximum_model_calls: number; usage: Record<string, number>;
    returned_models: string[]; requested_model: string; calls: CallEntry[]; started_at?: string; finished_at?: string;
    automatic_retries?: number; provider_requests?: number; response_format?: string; provider_events?: ProviderEvent[];
    sandbox: { mode: string; isolation: string } };
  inputs?: { code_files: { path: string; bytes: number }[]; papers: { name: string; pages: number | null; characters: number; source: string }[]; notes: string[];
    sources: { kind: string; name: string; source: string }[] };
  context?: { python_files: string[]; code_files_shown: string[]; code_files_not_shown: string[]; papers: { name: string; truncated: boolean }[] };
  request?: { question: string; links: { paper_url: string | null; code_url: string | null }; reused_inputs_from?: string | null; max_output_tokens?: number; follow_up?: boolean };
  connection?: { model: string | null; preferred_model: string; model_note: string | null; checked_at: string };
  provider_events?: ProviderEvent[];
  overview?: Overview;
  experiments: Experiment[]; verification: { files_verified: number; evaluations_recomputed: number } | null; export_available: boolean;
}

export const active = (state?: string) => state === 'queued' || state === 'running';
export const canWrite = (contract: Contract | null) => Boolean(contract && !isEvidenceBuild && !contract.read_only);

export class ApiError extends Error { constructor(message: string, public status: number) { super(message); } }
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await projectFetch(path, init);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof body.detail === 'string' ? body.detail : response.status === 422 ? 'Some settings are not valid.' : `The request failed (HTTP ${response.status}).`;
    throw new ApiError(detail, response.status);
  }
  return body as T;
}
export function action<T>(path: string, name: string, body: unknown = {}): Promise<T> {
  return api<T>(path, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CounterLab-Action': name }, body: JSON.stringify(body) });
}

// Store ---------------------------------------------------------------------
interface LabState { contract: Contract | null; items: ListItem[]; error: string; loaded: boolean; updated: number }
let state: LabState = { contract: null, items: [], error: '', loaded: false, updated: 0 };
const listeners = new Set<() => void>();
function emit(next: Partial<LabState>) { state = { ...state, ...next }; listeners.forEach(listener => listener()); }
export function useLab(): LabState {
  return useSyncExternalStore(listener => { listeners.add(listener); return () => listeners.delete(listener); }, () => state);
}
let inflight: Promise<void> | null = null;
export function refreshLab(): Promise<void> {
  if (inflight) return inflight;
  inflight = Promise.all([api<Contract>('/api/open-lab'), api<{ items: ListItem[] }>('/api/open-investigations')])
    .then(([contract, list]) => emit({ contract, items: list.items, error: '', loaded: true, updated: Date.now() }))
    .catch(cause => emit({ error: cause instanceof Error ? cause.message : 'CounterLab could not be reached.', loaded: true }))
    .finally(() => { inflight = null; });
  return inflight;
}
export function patchContract(change: Partial<Contract>) {
  if (state.contract) emit({ contract: { ...state.contract, ...change } });
}

// Toasts --------------------------------------------------------------------
export interface Toast { id: number; tone: 'good' | 'bad' | 'neutral'; text: string }
let toasts: Toast[] = [];
const toastListeners = new Set<() => void>();
export function useToasts(): Toast[] {
  return useSyncExternalStore(listener => { toastListeners.add(listener); return () => toastListeners.delete(listener); }, () => toasts);
}
let toastId = 0;
export function toast(text: string, tone: Toast['tone'] = 'neutral') {
  const id = ++toastId;
  toasts = [...toasts.slice(-3), { id, tone, text }];
  toastListeners.forEach(listener => listener());
  setTimeout(() => dismissToast(id), tone === 'bad' ? 8000 : 4500);
}
export function dismissToast(id: number) {
  toasts = toasts.filter(item => item.id !== id);
  toastListeners.forEach(listener => listener());
}

// Composer draft: files dropped on Home, or "Run again" from an investigation.
export interface Picked { file: File; role: Role }
export interface Draft { files: Picked[]; question?: string; allowance?: number; followUp?: boolean }
let draft: Draft = { files: [] };
export function setDraft(next: Draft) { draft = next; }
export function takeDraft(): Draft { const value = draft; draft = { files: [] }; return value; }

// Formatting ----------------------------------------------------------------
export function kilobytes(bytes: number) { return bytes < 1024 ? `${bytes} B` : bytes < 1048576 ? `${(bytes / 1024).toFixed(1)} kB` : `${(bytes / 1048576).toFixed(1)} MB`; }
export function num(value: number | null | undefined) {
  if (value === null || value === undefined) return '—';
  if (Number.isInteger(value) && Math.abs(value) < 1e15) return value.toLocaleString('en-US');
  if (Math.abs(value) >= 1000) return value.toLocaleString('en-US', { maximumFractionDigits: 1 });
  return Number(value.toPrecision(4)).toString();
}
export function duration(seconds: number | null | undefined) {
  if (seconds === null || seconds === undefined || !Number.isFinite(seconds)) return '—';
  if (seconds < 60) return `${Math.max(1, Math.round(seconds))} s`;
  const minutes = Math.floor(seconds / 60), rest = Math.round(seconds % 60);
  return minutes < 60 ? `${minutes} min ${rest.toString().padStart(2, '0')} s` : `${Math.floor(minutes / 60)} h ${minutes % 60} min`;
}
export function when(value: string) {
  const time = new Date(value).getTime();
  const seconds = (Date.now() - time) / 1000;
  if (!Number.isFinite(seconds)) return '';
  if (seconds < 45) return 'just now';
  if (seconds < 3600) return `${Math.round(seconds / 60)} min ago`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)} h ago`;
  return new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}
export function exact(value: string) {
  return new Date(value).toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' });
}
export function shortModel(model?: string | null) {
  if (!model) return 'Nemotron';
  return model.replace(/^nvidia\//i, '').replaceAll('-', ' ').replace(/\b(\d+)b\b/gi, '$1B').replace(/\ba(\d+)b\b/gi, 'A$1B');
}
export const STATE_LABEL: Record<string, string> = {
  queued: 'Queued', running: 'Running', completed: 'Completed', needs_review: 'Needs review', failed: 'Failed', cancelled: 'Stopped',
};
export function stateLabel(value: string) { return STATE_LABEL[value] ?? value.replaceAll('_', ' '); }
export function stateTone(value: string): 'good' | 'bad' | 'warn' | 'run' | 'neutral' {
  return value === 'completed' ? 'good' : value === 'failed' ? 'bad' : value === 'needs_review' ? 'warn' : active(value) ? 'run' : 'neutral';
}
export function runTitle(item: { title?: string | null; question: string }) {
  return item.title || item.question;
}
export const PAPER_SUFFIXES = ['.pdf', '.tex', '.md', '.markdown', '.rst', '.txt'];
export function guessRole(name: string): Role {
  const lower = name.toLowerCase();
  if (lower === 'readme.md' || lower.endsWith('requirements.txt')) return 'code';
  return PAPER_SUFFIXES.some(suffix => lower.endsWith(suffix)) ? 'paper' : 'code';
}
export function encode(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(',', 2)[1] ?? '');
    reader.onerror = () => reject(new Error(`${file.name} could not be read.`));
    reader.readAsDataURL(file);
  });
}

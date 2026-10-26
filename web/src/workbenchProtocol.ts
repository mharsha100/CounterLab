export interface WorkbenchSettings {
  family: 'known_witness' | 'uniform' | 'cyclic' | 'all_fit'; capacity: number; length: number;
  request_seed: number; algorithm_seed: number; forecast: 'fixed_witness' | 'perfect' | 'inverted'; tau: number;
  predict_gate_difference: boolean | null; predict_miss_difference: boolean | null;
}
export type ProtocolTemplate = { version: string; scope: string; counting_window: string;
  held_fixed: string[]; implementation_sha256: Record<string, string> };
export type WorkbenchPlan = { protocol: ProtocolTemplate & { settings: WorkbenchSettings }; protocol_sha256: string };

export function canonicalValue(value: unknown): string {
  function ordered(item: unknown): unknown {
    if (item === null || typeof item === 'string' || typeof item === 'boolean') return item;
    if (typeof item === 'number' && Number.isSafeInteger(item)) return item;
    if (Array.isArray(item)) return item.map(ordered);
    if (typeof item === 'object' && item !== null) return Object.fromEntries(Object.keys(item).sort().map(key => [key, ordered((item as Record<string, unknown>)[key])]));
    throw new Error('The plan contains an unsupported value. Use the bounded integer settings.');
  }
  return JSON.stringify(ordered(value)) + '\n';
}

export async function valueHash(value: unknown): Promise<string> {
  if (!globalThis.crypto?.subtle) throw new Error('Plan fingerprints require HTTPS or localhost.');
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(canonicalValue(value)));
  return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
}

export function settingsError(settings: WorkbenchSettings): string {
  for (const [field, low, high] of [['capacity', 1, 16], ['length', 1, 512], ['request_seed', 0, 4294967295],
    ['algorithm_seed', 0, 4294967295], ['tau', 0, 4]] as const) {
    if (!Number.isSafeInteger(settings[field]) || settings[field] < low || settings[field] > high) return `${field.replaceAll('_', ' ')} must be an integer from ${low} to ${high}.`;
  }
  if (settings.length < settings.capacity) return 'Include at least one full cache-sized warmup.';
  if (!['known_witness', 'uniform', 'cyclic', 'all_fit'].includes(settings.family)) return 'Choose a reviewed request family.';
  if (settings.family === 'known_witness') {
    if (settings.capacity !== 16 || settings.length !== 30 || settings.forecast !== 'fixed_witness' || settings.tau !== 0) return 'The known witness keeps its original fixed definition.';
  } else if (!['perfect', 'inverted'].includes(settings.forecast)) return 'Choose perfect or inverted synthetic forecasts.';
  if (settings.family !== 'uniform' && settings.request_seed !== 0) return 'Only uniform requests use a request seed; use zero otherwise.';
  for (const value of [settings.predict_gate_difference, settings.predict_miss_difference]) {
    if (value !== null && typeof value !== 'boolean') return 'Use agree, differ or abstain for each prediction.';
  }
  return '';
}

export async function commitPlan(template: ProtocolTemplate, settings: WorkbenchSettings): Promise<WorkbenchPlan> {
  const error = settingsError(settings);
  if (error) throw new Error(error);
  const protocol = { ...structuredClone(template), settings: { ...settings } };
  return { protocol, protocol_sha256: await valueHash(protocol) };
}

// Checks only archive bytes. No ZIP extraction, numerical replay or execution.
export const MAX_ARCHIVE_BYTES = 16 * 1024 * 1024;
export interface ArchiveFingerprint { sha256: string; bytes: number }

export function validateFingerprint(value: ArchiveFingerprint): ArchiveFingerprint {
  if (!/^[0-9a-f]{64}$/.test(value.sha256) || !Number.isSafeInteger(value.bytes) || value.bytes < 4 || value.bytes > MAX_ARCHIVE_BYTES) {
    throw new Error('The archive fingerprint is missing or unsupported. Restart the updated local app or use a fresh portable release.');
  }
  return value;
}

export async function verifyArchiveBytes(bytes: Uint8Array, expected: ArchiveFingerprint): Promise<string> {
  validateFingerprint(expected);
  if (bytes.byteLength !== expected.bytes) throw new Error('Archive size check failed. No download was prepared.');
  if (bytes[0] !== 0x50 || bytes[1] !== 0x4b || bytes[2] !== 0x03 || bytes[3] !== 0x04) {
    throw new Error('The response is not the expected ZIP archive. No download was prepared.');
  }
  if (!globalThis.crypto?.subtle) throw new Error('Checksum checks require HTTPS or localhost in a supported browser.');
  const hash = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new Uint8Array(bytes).buffer)), byte => byte.toString(16).padStart(2, '0')).join('');
  if (hash !== expected.sha256) throw new Error('Archive checksum check failed. No download was prepared.');
  return hash;
}

export async function receiveArchive(response: Response, fingerprint: ArchiveFingerprint,
  progress: (bytes: number) => void, signal: AbortSignal): Promise<Uint8Array> {
  const expected = validateFingerprint(fingerprint);
  if (!response.ok) throw new Error(`Package download failed (HTTP ${response.status}). No download was prepared.`);
  const mime = response.headers.get('Content-Type')?.split(';')[0].trim().toLowerCase();
  // Windows/Python and static hosts may use either ZIP label or generic binary.
  // The file signature, exact length and expected SHA-256 remain mandatory.
  if (!mime || !['application/zip', 'application/x-zip-compressed', 'application/octet-stream'].includes(mime) || !response.body) {
    throw new Error('The server did not return a ZIP archive. No download was prepared.');
  }
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  const cancel = () => { void reader.cancel().catch(() => {}); };
  signal.addEventListener('abort', cancel, { once: true });
  try {
    signal.throwIfAborted();
    while (true) {
      const { value, done } = await reader.read();
      signal.throwIfAborted();
      if (done) break;
      total += value.byteLength;
      if (total > expected.bytes) throw new Error('Archive exceeds its declared size. No download was prepared.');
      chunks.push(value);
      progress(total);
    }
    if (total !== expected.bytes) throw new Error('Archive was incomplete. No download was prepared.');
    const result = new Uint8Array(total);
    let offset = 0;
    for (const chunk of chunks) { result.set(chunk, offset); offset += chunk.byteLength; }
    return result;
  } catch (error) {
    await reader.cancel().catch(() => {});
    throw error;
  } finally {
    signal.removeEventListener('abort', cancel);
    reader.releaseLock();
  }
}

// Record the exact local inputs and emitted files after a successful Vite build.
// This detects stale/changed files; it is not a signature or trusted timestamp.
import { createHash } from 'node:crypto';
import { readdir, readFile, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const web = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const root = path.dirname(web);
const output = process.argv[2];
if (!['dist', 'judge-dist'].includes(output)) throw new Error('Choose dist or judge-dist.');
const destination = path.join(web, output);
const name = 'counterlab-build.json';
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const stable = value => JSON.stringify(value, (_, item) => item && typeof item === 'object' && !Array.isArray(item)
  ? Object.fromEntries(Object.keys(item).sort().map(key => [key, item[key]])) : item);
async function files(directory) {
  const names = [];
  for (const item of await readdir(directory, { withFileTypes: true })) {
    if (item.name === '.env' || item.name.startsWith('.env.') || ['.npmrc', '.pypirc', '.netrc'].includes(item.name)) {
      throw new Error('Credential files cannot be included in frontend inputs or assets.');
    }
    if (item.isSymbolicLink()) throw new Error('Build fingerprints cannot follow symbolic links.');
    const target = path.join(directory, item.name);
    if (item.isDirectory()) names.push(...await files(target));
    else if (item.isFile()) names.push(target);
  }
  return names.sort();
}
async function fingerprints(names, relativeTo) {
  const entries = [];
  for (const file of names) {
    const bytes = await readFile(file);
    entries.push([path.relative(relativeTo, file).split(path.sep).join('/'), { bytes: bytes.length, sha256: sha(bytes) }]);
  }
  return Object.fromEntries(entries.sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0));
}
const inputNames = [
  ...await files(path.join(web, 'src')), ...await files(path.join(web, 'public')),
  ...await files(path.join(web, 'scripts')),
  ...['index.html', 'package.json', 'package-lock.json', 'tsconfig.json', 'vite.config.ts'].map(file => path.join(web, file)),
];
if (!(await stat(path.join(destination, 'index.html'))).isFile()) throw new Error('Built index.html is missing.');
const inputs = await fingerprints(inputNames, root);
const outputs = await fingerprints((await files(destination)).filter(file => path.basename(file) !== name), destination);
const manifest = { schema: 1, purpose: 'local_build_fingerprints', mode: output === 'dist' ? 'application' : 'recorded_evidence',
  inputs, inputs_sha256: sha(Buffer.from(stable(inputs))), outputs,
  limit: 'Fingerprints detect changes relative to this local build record; they are not signatures or trusted timestamps.' };
await writeFile(path.join(destination, name), JSON.stringify(manifest, null, 2) + '\n');
process.stdout.write(`Build record saved: ${Object.keys(inputs).length} inputs, ${Object.keys(outputs).length} outputs.\n`);

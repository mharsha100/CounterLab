export const routes = {
  home: { view: 'home', label: 'Home' },
  lab: { view: 'lab', label: 'New investigation' },
  runs: { view: 'runs', label: 'Investigations' },
  run: { view: 'run', label: 'Investigation' },
  settings: { view: 'settings', label: 'Settings' },
  demo: { view: 'demo', label: 'Guided demonstration' },
  investigation: { view: 'investigation', label: 'Paging case investigation' },
  sources: { view: 'sources', label: 'Claim audit' },
  'claim-audit': { view: 'sources', label: 'Claim audit' },
  'source-cards': { view: 'sources', label: 'Original source cards' },
  research: { view: 'research', label: 'Controlled study' },
  'controlled-study': { view: 'research', label: 'Controlled study' },
  'source-reproduction': { view: 'research', label: 'Source reproduction' },
  'source-investigator': { view: 'research', label: 'Source investigator' },
  'experiment-workbench': { view: 'research', label: 'Design an experiment' },
  evaluation: { view: 'evaluation', label: 'Original evaluation' },
  'source-evaluation': { view: 'evaluation', label: 'Fresh source evaluation' },
  evidence: { view: 'evidence', label: 'Evidence library' },
  'selected-evidence': { view: 'evidence', label: 'Selected investigation evidence' },
  history: { view: 'history', label: 'Case run history' },
} as const;
export type Route = keyof typeof routes;
export type View = typeof routes[Route]['view'];
export const caseViews: readonly View[] = ['demo', 'investigation', 'sources', 'research', 'evaluation', 'evidence', 'history'];

// Query parameters that belong to a view. They are cleared when the view changes
// unless given again, so a shared link always reproduces the same screen.
export const viewParams = ['id', 'tab', 'from', 'example', 'status', 'q'] as const;
export type ViewParam = typeof viewParams[number];

export function routeFromSearch(search: string): Route {
  const query = new URLSearchParams(search);
  const value = query.get('view') || '';
  if (Object.hasOwn(routes, value)) return value as Route;
  return 'home';
}

export function pathForRoute(currentUrl: string, route: Route, params: Partial<Record<ViewParam, string>> = {}): string {
  if (!Object.hasOwn(routes, route)) throw new Error('Unknown workspace view.');
  const url = new URL(currentUrl);
  for (const name of viewParams) url.searchParams.delete(name);
  url.searchParams.delete('run');
  url.searchParams.set('view', route);
  for (const [name, value] of Object.entries(params)) if (value) url.searchParams.set(name, value);
  url.hash = '';
  return `${url.pathname}${url.search}`;
}

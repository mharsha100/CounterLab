import { useSyncExternalStore, type MouseEvent } from 'react';
import { pathForRoute, routeFromSearch, type Route, type ViewParam } from './navigationProtocol';

const eventName = 'counterlab:navigation';
function subscribe(notify: () => void) {
  window.addEventListener('popstate', notify);
  window.addEventListener(eventName, notify);
  return () => { window.removeEventListener('popstate', notify); window.removeEventListener(eventName, notify); };
}
export function useRoute(): Route {
  return useSyncExternalStore(subscribe, () => routeFromSearch(window.location.search));
}
export function useParam(name: ViewParam): string {
  return useSyncExternalStore(subscribe, () => new URLSearchParams(window.location.search).get(name) ?? '');
}
export function hrefFor(route: Route, params: Partial<Record<ViewParam, string>> = {}): string {
  return pathForRoute(window.location.href, route, params);
}
export function navigateTo(route: Route, params: Partial<Record<ViewParam, string>> = {}, replace = false) {
  const path = pathForRoute(window.location.href, route, params);
  if (path !== `${window.location.pathname}${window.location.search}${window.location.hash}`) {
    if (replace) window.history.replaceState(null, '', path); else window.history.pushState(null, '', path);
    window.dispatchEvent(new Event(eventName));
  }
}
export function setParam(name: ViewParam, value: string) {
  const url = new URL(window.location.href);
  if (value) url.searchParams.set(name, value); else url.searchParams.delete(name);
  window.history.replaceState(null, '', `${url.pathname}${url.search}`);
  window.dispatchEvent(new Event(eventName));
}
// Real links for navigation (middle-click and copy work); plain clicks stay in the app.
export function linkClick(route: Route, params: Partial<Record<ViewParam, string>> = {}) {
  return (event: MouseEvent<HTMLAnchorElement>) => {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    navigateTo(route, params);
  };
}

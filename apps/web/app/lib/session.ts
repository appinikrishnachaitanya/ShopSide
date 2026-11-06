/** Keep each tab's membership separate while keeping the membership token HttpOnly. */
const SESSION_KEY = 'shopside_browser_session';

function newSession(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, value => value.toString(16).padStart(2, '0')).join('');
}

export function browserSession(): string {
  let session = sessionStorage.getItem(SESSION_KEY);
  if (!session || !/^[a-f0-9]{32}$/.test(session)) {
    session = newSession();
    sessionStorage.setItem(SESSION_KEY, session);
  }
  return session;
}

export function startInviteSession(): void {
  sessionStorage.setItem(SESSION_KEY, newSession());
}

export function sessionFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  headers.set('X-ShopSide-Session', browserSession());
  return fetch(input, { ...init, headers });
}

export function sessionSocket(path: string): WebSocket {
  const url = new URL(path, location.origin);
  url.protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  url.searchParams.set('session', browserSession());
  return new WebSocket(url);
}

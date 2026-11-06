// Keep browser cookies and WebSockets on the frontend origin while selecting
// the backend at process startup, not at Next.js build time.
const http = require('node:http');
const next = require('next');
const httpProxy = require('http-proxy');
const {GoogleAuth} = require('google-auth-library');

const port = Number(process.env.PORT || 3000);
const hostname = '0.0.0.0';
const backend = process.env.BACKEND_URL || process.env.API_INTERNAL_URL || 'http://127.0.0.1:8000';
const target = new URL(backend);
if (!['http:', 'https:'].includes(target.protocol) || target.username || target.password || target.search || target.hash || (target.pathname && target.pathname !== '/')) {
  throw new Error('BACKEND_URL must be an HTTP(S) origin without credentials or a path');
}
const audience = process.env.BACKEND_ID_TOKEN_AUDIENCE;
const auth = audience ? new GoogleAuth() : null;
let identityClient;
async function proxyOptions() {
  if (!auth) return {};
  identityClient ||= await auth.getIdTokenClient(audience);
  const headers = await identityClient.getRequestHeaders();
  const authorization = typeof headers.get === 'function' ? headers.get('authorization') : (headers.Authorization || headers.authorization);
  if (!authorization) throw new Error('Could not obtain backend identity token');
  return {headers: {authorization}};
}
const app = next({dev: process.env.NODE_ENV !== 'production', hostname, port});
const proxy = httpProxy.createProxyServer({target: target.origin, changeOrigin: true, ws: true, xfwd: true});
proxy.on('error', (_error, _request, response) => {
  if (response && typeof response.writeHead === 'function') {
    if (!response.headersSent) response.writeHead(502, {'Content-Type': 'application/json'});
    response.end(JSON.stringify({detail: 'Backend unavailable'}));
  } else if (response && typeof response.destroy === 'function') response.destroy();
});
app.prepare().then(() => {
  const handler=app.getRequestHandler();
  const upgrade=app.getUpgradeHandler();
  const server=http.createServer((req,res) => {
    const path=new URL(req.url, 'http://frontend.invalid').pathname;
    if (path === '/api' || path.startsWith('/api/')) {
      proxyOptions().then(options => proxy.web(req,res,options)).catch(() => {res.writeHead(502, {'Content-Type':'application/json'});res.end(JSON.stringify({detail:'Backend authentication unavailable'}));});
    } else handler(req,res);
  });
  server.on('upgrade',(req,socket,head) => {
    const path=new URL(req.url, 'http://frontend.invalid').pathname;
    if (path === '/api' || path.startsWith('/api/')) {
      proxyOptions().then(options => proxy.ws(req,socket,head,options)).catch(() => socket.destroy());
    } else upgrade(req,socket,head);
  });
  server.listen(port,hostname,()=>console.log(`Frontend listening on port ${port}`));
}).catch(() => { console.error('Could not start frontend'); process.exit(1); });

// 模拟「内网服务」：只在 loopback 监听，公网/外部网络不可达。
// 任何打到这里的请求都必然来自本机其它进程（即 Vane 的服务端浏览器）。
import http from 'node:http';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

const LOG = fileURLToPath(new URL('./canary-log.jsonl', import.meta.url));
const FLAG = 'VANE_SSRF_CANARY_8842_THIS_PAGE_IS_NOT_INTERNET_ACCESSIBLE';

const server = http.createServer((req, res) => {
  const entry = {
    time: new Date().toISOString(),
    method: req.method,
    url: req.url,
    host: req.headers.host,
    userAgent: req.headers['user-agent'],
    remoteAddress: req.socket.remoteAddress,
    remotePort: req.socket.remotePort,
  };
  fs.appendFileSync(LOG, JSON.stringify(entry) + '\n');
  console.log('[CANARY HIT]', JSON.stringify(entry));

  if (req.url.startsWith('/internal/secret')) {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(`<!doctype html><html><head><title>Internal Secret Page</title></head>
<body><article>
<h1>Internal Secret</h1>
<p>This page is only reachable from the internal loopback interface. It must never be fetched by an internet-facing service.</p>
<p><strong>FLAG: ${FLAG}</strong></p>
<p>Additional internal note: payroll export for 2026-Q3 is stored on the shared drive. Access is restricted to the finance VLAN.</p>
</article></body></html>`);
  } else {
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end('not found');
  }
});

server.listen(8787, '127.0.0.1', () => {
  console.log('[CANARY] internal service listening on http://127.0.0.1:8787 (loopback only)');
});

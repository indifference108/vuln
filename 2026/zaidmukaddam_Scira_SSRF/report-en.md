# Vulnerability Report

> Report ID: VUL-2026-SCIRA-SSRF-001
> Reporter: {{to be filled}}
> Date: 2026-09-30
> Target program: CVE (GitHub Security Advisory / CNA)

---

## 1. Product Introduction

Scira is an open-source AI-powered search engine developed by zaidmukaddam (about 11.9k GitHub stars, formerly MiniPerplx). It is built on Next.js and answers questions with cited web sources. It is distributed for self-hosting and is also operated officially at scira.ai. The vulnerability resides in its image proxy endpoint `/api/proxy-image`.

## 2. Vulnerability Title

Server-Side Request Forgery in zaidmukaddam Scira /api/proxy-image (through commit e1692f5)

## 3. Summary / Description

Scira through commit e1692f5 (2026-08-13, latest main at time of testing) is affected by a server-side request forgery in the `url` parameter of `/api/proxy-image`. An unauthenticated remote attacker can make the server send requests to arbitrary URLs, including loopback, private-network, and cloud metadata addresses, and read the responses, resulting in a confidentiality impact. The official deployment scira.ai is also affected; its responses are cached at the Vercel edge with a one-year immutable policy, so an attacker can serve arbitrary content from the trusted scira.ai origin.

## 4. Technical Analysis / Root Cause

**Weakness**: CWE-918 Server-Side Request Forgery

**Source-to-sink chain**:
```
user input (url query parameter, app/api/proxy-image/route.ts GET(), line 5)
  → line 12-16: only new URL(url) syntax validation; no scheme/address/host checks
  → fetch(url) (sink, route.ts line 19)
  → response body and Content-Type returned to the caller (route.ts lines 30-38)
```

**Code location**:
```text
File: app/api/proxy-image/route.ts (commit e1692f5)
Lines: 5 (source), 12-16 (only validation), 19 (sink), 30-38 (response passthrough)
Relevant code:
  const url = request.nextUrl.searchParams.get('url');
  try { new URL(url); } catch { return NextResponse.json({ error: 'Invalid URL' }, { status: 400 }); }
  const response = await fetch(url, { headers: { 'User-Agent': 'Mozilla/5.0 ...' } });
  const contentType = response.headers.get('content-type') || 'image/jpeg';
  return new NextResponse(response.body, { headers: {
    'Content-Type': contentType,
    'Cache-Control': 'public, max-age=31536000, immutable',
    'Access-Control-Allow-Origin': '*',
  }});
```

**Validity check** (per code-audit §8):
- Reachable: `/api/proxy-image` is a public route; confirmed on scira.ai (`X-Matched-Path: /api/proxy-image`).
- Controllable: the `url` parameter is fully attacker-controlled; only syntax is checked.
- Propagable: no authentication, allowlist, or address validation between source and sink.
- Exploitable: verified — the server fetched a loopback canary and returned its secret token.
- Bypassable: no effective protection exists; even a hypothetical initial-URL check is defeated by redirect following (verified with a 302 into loopback).
- Reproducible: stable across an 8-case matrix on a clean default install; raw request included in audit-findings.md.
- Impact established: loopback/private-network/metadata content is readable — confidentiality impact.
- Impact scope: chains into internal scanning, cloud credential theft, and edge cache poisoning.

**Root cause**: The endpoint passes the user-supplied `url` directly to a server-side `fetch` with only URL syntax validation. It does not restrict the scheme, the resolved address, or the response content type, so the server visits any attacker-chosen address from its own network position and returns what it reads.

## 5. Affected Versions

- **Affected**: all versions through commit e1692f5 (2026-08-13); the project publishes no releases/tags, and the vulnerable code has been present since its introduction
- **Not affected**: none confirmed
- **Fixed version**: no fix available as of the report date
- **Tested environment**: commit e1692f5 / WSL2 Ubuntu 26.04 / Node.js 22.20 / Next.js dev server; production verification on scira.ai (Vercel)

## 6. Severity

| Item | Value |
|------|-------|
| CVSS v3.1 score | 7.5 |
| CVSS v3.1 vector | `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N` |
| CVSS v4.0 score | 7.7 |
| CVSS v4.0 vector | `CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:N/VI:N/VA:N/SC:H/SI:N/SA:N` |
| Rating | High |

> Scoring rationale: no authentication (PR:N), network-reachable (AV:N), single request (AC:L, UI:N); the server reads internal and cloud metadata content, a high confidentiality impact (v3.1 C:H; in v4.0 the impact falls on subsequent systems, SC:H). Scores recomputed with the FIRST reference algorithm; vectors and scores are consistent.
> Note: if the CNA considers the impact to cross the component's security scope, v3.1 `S:C` yields 8.6 — still High.

## 7. CVSS Vector

```
CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N
CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:N/VI:N/VA:N/SC:H/SI:N/SA:N
```

## 8. Reproduction Steps

### 8.1 Environment

- Product/version: Scira commit e1692f5
- OS/runtime: WSL2 Ubuntu 26.04, Node.js 22.20 (PostgreSQL 16 and Redis 7 containers)
- Network position: local self-hosted instance; additional read-only verification on the public scira.ai
- Test account: none

### 8.2 Steps

**Step 1 — Confirm the proxy baseline**
Request `/api/proxy-image?url=https://httpbin.org/image/png`. The server returns 200 with the PNG, confirming it fetches arbitrary URLs.
> Evidence: evidence/01-wsl-repro-captures-20260929.txt (T1)

**Step 2 — Send the malicious request**
Start a read-only canary service on 127.0.0.1:8899 that returns a random token, then:
```http
GET /api/proxy-image?url=http%3A%2F%2F127.0.0.1%3A8899%2F HTTP/1.1
Host: {{TARGET}}
```

**Step 3 — Observe the result**
The response is 200 with the canary token in the body — the server read loopback content and returned it:
```
HTTP/1.1 200 OK
Content-Type: text/plain

SCIRA_SSRF_CANARY_1790697885
```
> Evidence: evidence/01-wsl-repro-captures-20260929.txt (T3)

**Step 4 — Verify impact**
Two further checks. First, a 302 redirect (`url=http://127.0.0.1:8900/hop` → canary) also returns the token, proving that fetch follows redirects and any initial-URL-only fix can be bypassed. Second, against the official scira.ai, requesting a self-hosted webhook.site canary URL returned 200 with the canary body, `Content-Type: text/html` passed through, and `X-Vercel-Cache: HIT` with `Cache-Control: public, max-age=31536000, immutable` — the production deployment is vulnerable, and attacker-planted content is cached at the edge under the scira.ai origin for a year.
> Evidence: evidence/01-wsl-repro-captures-20260929.txt (T8), evidence/04-scira-ai-production-20260928.txt

## 9. Proof of Concept

### 9.1 Format selection

- Chosen format: nuclei template + custom Python script (both in poc/)
- Rationale: the vulnerability is a single stateless request, so nuclei is the lightest fit; the custom script additionally covers the loopback canary and 302 redirect cases and proxies to Burp by default for per-packet analysis

### 9.2 Usage

- Runtime: Python 3 (requests) / nuclei
- **Proxy to Burp**: `USE_BURP=1 BURP_PROXY=http://127.0.0.1:8080 python3 poc.py`; nuclei: `-proxy http://127.0.0.1:8080`
- Disclaimer: for authorized testing and vulnerability verification only; all requests are read-only.

### 9.3 POC Code

nuclei (`poc/scira-proxy-image-ssrf-nuclei.yaml`; payload points at the public httpbin echo endpoint, no internal targets):
```bash
nuclei -t poc/scira-proxy-image-ssrf-nuclei.yaml -u http://{{TARGET}}/
```

Custom script (`poc/poc.py`; target via environment variable, canary token randomized per run):
```bash
TARGET=http://{{TARGET}} USE_BURP=1 python3 poc/poc.py
```

### 9.4 Expected output / success criteria
```
== 1. baseline ==            [+] proxy works
== 2. loopback SSRF ==       [+] server read loopback canary token
== 3. redirect into loopback ==  [+] fetch followed 302 into loopback
[*] 3/3 passed — SSRF confirmed (exit code 0)
```
> Captured run: evidence/05-poc-py-run-output-20260930.txt

## 10. Mitigation / Fix Recommendations

### 10.1 Temporary mitigations
- Restrict server egress at the network layer: block loopback, private ranges, and 169.254.0.0/16.
- Take `/api/proxy-image` offline if image proxying is not essential.
- Drop the long-lived immutable `Cache-Control` on this route so already-planted content stops hitting the edge cache.

### 10.2 Root-cause fixes
- Allow only `http`/`https`; resolve the hostname and reject loopback, private, link-local, and reserved addresses; repeat the check after every redirect hop (or disable redirect following).
- Prefer an allowlist of image source hostnames where the use case permits.
- Require `Content-Type: image/*` (verify magic bytes), and cap response size (e.g. 5 MB) and timeout.
- Remove the wildcard CORS header.

### 10.3 Verification
Replay poc/poc.py and the nuclei template: the baseline request should still succeed, while the loopback and redirect cases must be rejected — the three checks no longer all pass.

## 11. False-Positive Elimination / Impact Justification

```
False-positive verification:
- Existence: ✅ reproduced on a clean default install (8-case matrix, poc.py 3/3, ≥3 runs); read-only verification on scira.ai also positive
- Characterization: ✅ a real server-side request forgery (CWE-918) with confidentiality impact
- Exploitability: ✅ no authentication (PR:N), internet-reachable (AV:N), single request, deterministic impact
- Novelty: ✅ no match in NVD/cve.org, GitHub Advisories (none published for the repo), repo issues ("ssrf", 0 hits), or public writeups; root cause is in the project's own code, not a known dependency CVE
- Evidence: ✅ full request/response captures (T1-T8), production curl session, source location with line numbers, captured POC run
- Code-audit validity (with source): ✅ reachable/controllable/propagable/exploitable/bypassable/reproducible/impact established/impact scope — all eight pass
Conclusion: confirmed real, exploitable, and previously undisclosed — ready for submission.
```

---

## Appendix A: Timeline / References

| Date | Event |
|------|-------|
| 2026-09-28 | Discovered and verified (self-hosted + read-only check on scira.ai) |
| 2026-09-29 | 8-case reproduction matrix on clean WSL install; root cause located |
| 2026-09-30 | poc.py / nuclei template verified; report finalized |
| (pending) | Reported to maintainer via GitHub Security Advisory |

- Vulnerable source: https://github.com/zaidmukaddam/scira/blob/main/app/api/proxy-image/route.ts
- Project site: https://scira.ai
- Related CVE/CNVD/CNNVD: none assigned yet

## Appendix B: Evidence Checklist

- [x] HTTP request/response captures (evidence/01, 02 — raw T1-T8)
- [x] Production verification session (evidence/04)
- [x] Source-level root-cause evidence (evidence/03-vulnerable-route.ts)
- [x] Captured POC run (evidence/05)
- [ ] Reproduction screenshots (raw captures and script output used instead; screenshots can be taken per §8 if required)
- [ ] Version-diff / patch comparison (no official patch yet)

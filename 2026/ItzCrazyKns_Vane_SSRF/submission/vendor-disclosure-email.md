Subject: Security Vulnerability Report: Unauthenticated SSRF in Vane scrape_url tool (CWE-918, CVSS 7.5)

Hi Kushagra,

I'm indifference108, a security researcher. I'm reporting a security
vulnerability in Vane (https://github.com/ItzCrazyKns/Vane). This was
already publicly reported in issue #1140 (2026-05-25); this message is
a courtesy heads-up with an independent reproduction, a complete
report group, and concrete fix recommendations.

Summary: The /api/search endpoint (src/app/api/search/route.ts,
verified at commit 348feca, v1.12.2) requires no authentication. The
Researcher agent's scrape_url tool passes LLM-supplied URLs verbatim to
Scraper.scrape() (src/lib/scraper.ts:70), which executes
page.goto(url) via a server-side Playwright browser launched with
--no-sandbox. No scheme, hostname, or IP validation is performed at any
point. An unauthenticated remote attacker can induce the LLM — via the
query text or prompt injection in fetched content — to make the server
request arbitrary URLs: loopback and private-network services, cloud
metadata endpoints (e.g. http://169.254.169.254/), and, because
schemes are unrestricted, local files via file:// URLs. Fetched content
is echoed back to the attacker in the API response.

Severity: CWE-918, CVSS v3.1 7.5 (High)
Vector:   CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N
          CVSS v4.0 8.7 (High)

Full technical details (source-to-sink root-cause analysis with exact
files and line numbers), reproduction steps, a non-destructive
read-only PoC (verified end-to-end against a local deployment with a
deterministic mock LLM and loopback canary), and fix recommendations
are published in my disclosure repository:

https://github.com/indifference108/vuln/tree/main/2026/ItzCrazyKns_Vane_SSRF

All testing was read-only and performed against my own deployment; the
PoC uses self-hosted canary targets only.

Fix recommendations (details in the repository):
1. Validate URLs at the entry of Scraper.scrape (or scrapeURL.ts):
   allow only http/https, resolve hostnames and reject private,
   loopback, link-local and reserved ranges (mitigate DNS rebinding),
   default-deny with an allowlist.
2. Remove --no-sandbox from the Playwright launch args.
3. Add authentication or rate limiting to /api/search.

Two requests:
1. Please acknowledge this report and issue #1140. If you prefer a
   private channel, I'm happy to resubmit through a GitHub Security
   Advisory draft.
2. A CVE ID request has been submitted to MITRE CNA-LR (tracking
   number CAN-2026-2038643, under review). As the maintainer you can
   instead request a CVE through a GitHub Security Advisory ("Request
   CVE"), which also lets you control the advisory text — just let me
   know and I will withdraw the CNA-LR request.

Thank you for maintaining Vane.

Best regards,
indifference108

https://github.com/indifference108

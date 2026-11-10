# Hard-coded Signature Secret in a Unified Authentication Gateway Enables Authentication Bypass (Redacted)

## 1. Summary

| Field | Value |
|---|---|
| Title | Hard-coded appSecret in a publicly served front-end bundle allows forged signatures to bypass the first authentication gate of a cardLoginAuth unified-authentication flow |
| Type | Authentication bypass / hard-coded cryptographic key (CWE-798, CWE-321, CWE-287) |
| Severity | High |
| Affected asset | China Mobile subsidiary unified-authentication gateway domain and its one-tap login / SIM-card authorization chain |
| Discovery | Authorized, non-destructive, minimal verification: public front-end asset review plus an end-to-end control experiment |
| Authorization | 1241323141382 (2026-11-05 — 2026-11-08) |
| Verification window | 2026-11-05 18:15—18:19 (UTC+8) |

## 2. Root cause

The cardLoginAuth entry point of the unified-authentication gateway relies on a client-computed signature as its first identity check. The signature is derived from client-generated, non-secret fields combined with a shared secret. That secret is hard-coded in a publicly downloadable front-end SPA bundle of the developer portal, so any anonymous visitor can retrieve it and recompute valid signatures offline.

A second signing endpoint in the same domain uses a formula that contains no secret at all and issues valid signature tokens to anonymous callers. Together, both the primary and auxiliary signature checks of the authentication chain are defeated.

## 3. Verification and evidence (redacted)

1. The signing secret was confirmed inline in the signing function of a public front-end asset (raw bundle and secret value are kept in the local evidence package).
2. A request signed with the leaked secret was accepted by the gateway and advanced to the next stage; a control request signed with an intentionally wrong secret was rejected with a signature-validation failure. The difference proves the server genuinely validates signatures and accepts only those produced with the leaked secret.
3. A separate control showed that an invalid business-type parameter short-circuits before signature validation; it was therefore excluded as a decision criterion.
4. Verification stopped strictly at "the flow can be advanced". No real phone number was submitted, no real login was completed, and no real user data was accessed.

## 4. Impact

- The signature mechanism, the first line of defence of the unified-authentication gateway, is invalidated; downstream checks rely only on the encrypted number and the number-binding relationship.
- An attacker can construct an authorization page on the official domain displaying any victim's number, creating a high-trust phishing surface.
- All business chains relying on this unified-authentication capability are affected.

## 5. Remediation

1. Revoke and rotate the leaked secret immediately; move all signing secrets server-side and never ship them to front-end code.
2. Audit every front-end bundle for similar hard-coded secrets and add a pre-release secret-scanning gate.
3. Bind the encrypted number to the request context, add a one-time challenge, and enforce timestamp/traceId replay protection at the authentication entry point.
4. Replace the secret-free signing endpoint with a server-issued challenge or an HMAC key distributed over a secure channel to a local SDK component, not to JavaScript.

## 6. Interim mitigation

Until rotation is complete, apply rate limiting and anomalous-source filtering to the authentication entry point, enforce number-range binding, and add an explicit second confirmation step on the authorization page.

> This is the public-archive version. Secret values, appId, the signing formula, endpoint details and runnable PoC are intentionally omitted. Submission text should be produced from the complete local material following the standard in notes.md section 6.

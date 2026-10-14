# Inter-School Course-Sharing Platform — Default Password Vulnerability (English Report)

## Key URLs (rule / KYC / login entry)

| Item | URL |
|------|-----|
| Password rule (first-hand) | https://jwc.henau.edu.cn/a/tongzhigonggao/jiaowuke/20260702/9127.html (Henan Agricultural University Academic Affairs Office, 2026-07-02; backup: https://jwc.henau.edu.cn/a/tongzhigigonggao/jiaowuke/20260115/7200.html , 2026-01-15) |
| Student-ID source (first-hand) | https://jgxy.henau.edu.cn/info/1045/3647.htm (College of Economics & Management, class-of-2025 major-distribution list xlsx with 178 full IDs, 2026-05-14) |
| Login entry | https://xjkchx.ncwu.edu.cn/ (redirects to https://xjkchx.ncwu.edu.cn/cas/login.action , Kingosoft kingo CAS) |

## Title

Inter-School Course-Sharing Platform (xjkchx.ncwu.edu.cn, operated by North China University of Water Resources and Electric Power, shared by a 6-university alliance) — Default Weak Password (initial password = student ID + "ny") Allowing Login to Any Student Account

## Summary

The "Inter-School Course-Sharing Platform" (https://xjkchx.ncwu.edu.cn/, publicly reachable; domain belongs to North China University of Water Resources and Electric Power, NCWU) has a weak-password vulnerability. The platform serves a six-university alliance (NCWU 10078, Henan Agricultural University 10466, Henan University of Chinese Medicine 10471, Henan University of Economics and Law 10484, Zhengzhou University of Aeronautics 10485, Henan Polytechnic University 10460). An attacker needs no authorization and no non-public information: the university itself publishes (1) the initial-password rule and (2) complete student ID numbers in official public notice attachments. Combining the two allows logging in as any enrolled student of Henan Agricultural University (and any alliance school with a similarly published rule).

Password rule (published by the university's Academic Affairs Office): username = student ID, initial password = **student ID + "ny"** (e.g., 2506821003 → 2506821003ny), published in two official course-selection notices (2026-01-15 and 2026-07-02). Student IDs (178 complete 10-digit IDs of current class-of-2025 undergraduates) are published in the official major-distribution list attachment (xlsx) by the College of Economics and Management (2026-05-14).

## Affected Product

- Product: Inter-School Course-Sharing Platform (Kingosoft kingo CAS customization, 6-university alliance)
- Entry: https://xjkchx.ncwu.edu.cn/ (login API: POST /cas/logon.action, DES+base64+md5-token encrypted parameters)
- Affected domain: xjkchx.ncwu.edu.cn (operated by NCWU); affected parties: students of all six alliance universities
- Scope: all class-of-2024/2025 undergraduates of Henan Agricultural University (named as the course-selection cohort in the notices, several thousand per class); other alliance schools are equally at risk where the initial-password rule is publicly documented
- Verified: 2026-10-14, public Internet, Node.js replication of the kingo encryption flow

## Root Cause

The root cause is a publicly derivable initial password (published by the university) combined with no forced password change on first login and weak login protection (CWE-521):

1. The Academic Affairs Office notice publicly documents: "username is the student ID; initial password is 'student ID + ny'". The system only verbally suggests changing the password — it does not enforce it.
2. Student IDs — 10-digit enumerable identifiers — are published in plaintext in an official xlsx attachment (178 IDs).
3. The login page states "no CAPTCHA under normal circumstances"; the account lock threshold is 5 wrong attempts per 24 hours — weak rate limiting; no anomalous-login alerting. Empirically, 3 of 4 tested IDs logged in with the initial password (75% hit rate).

Data flow: attacker reads the notice (password rule) → downloads the xlsx (student IDs) → selects "Henan Agricultural University" (sel_schname=10466) and POSTs /cas/logon.action (ID + ID+ny) → authentication succeeds (status 200) → full account access, including course selection/drop under the victim's identity.

## CVSS

- v3.1: **9.1 Critical** — `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N`
- CWE-521 (Weak Password Requirements)
- Rationale: network-reachable, no privileges or user interaction required; both credential elements come from official public sources; confidentiality and integrity impact are high (the platform's core write functions — course selection/drop — directly affect a victim's academic record; not exercised during verification); no availability impact.

## Proof of Concept

See `poc/verify_xjkchx_weakpass.js` (Node.js; read-only: replicates the kingo DES encryption login flow, one attempt per ID, stops on success, calls no business API). Core reproduction steps:

1. Visit https://jwc.henau.edu.cn/a/tongzhigonggao/jiaowuke/20260702/9127.html for the rule (ID + "ny").
2. Visit https://jgxy.henau.edu.cn/info/1045/3647.htm and download the attachment to obtain any class-of-2025 ID (e.g., 2506821003).
3. Open https://xjkchx.ncwu.edu.cn/, select 河南农业大学 (school code 10466), enter the ID as username and ID+ny as password.
4. Observed result (2026-10-14): login succeeded (CAS returned status 200, redirect to /frame/homes.action). Two further accounts succeeded the same way (3 total; list in `evidence/02-登录成功账号清单.txt`); a fourth account had already changed its password (HTTP 402).

## Impact

- Confidentiality (High): account takeover of any affected student; the platform stores course-selection records and personal information.
- Integrity (High): core functions (course selection/drop) can be abused under a victim's identity, directly affecting academic progress (no write operation was exercised during verification).
- Availability: none observed.
- Scope: all class-of-2024/2025 undergraduates of Henan Agricultural University; the platform is shared by six universities, and other alliance schools with similarly published rules are equally exposed.

## Remediation

Immediate: revoke the derivable initial password and batch-reset all accounts to random one-time passwords; require CAPTCHA on every login and tighten anomalous-login alerting (multi-account single-source attempts, off-campus networks).
Long-term: enforce first-login password change with complexity policy (ban ID-derived passwords); never derive initial passwords from the ID; mask ID columns in public xlsx attachments (first 4 + last 2 digits); add a pre-publication sensitive-data review.

## Reporter Statement

Verification was performed by the reporter: login authentication requests only, one attempt per ID, stopped after 4 IDs (3 succeeded, 1 already changed); no post-login business API was called; no data was read, modified, or deleted; no non-public information or unauthorized means were used. The vulnerability is original and previously undisclosed.

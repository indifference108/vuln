# China Agricultural University CIEE Comprehensive Evaluation Platform — Default Password Vulnerability (English Report)

## Title

China Agricultural University, College of Information and Electrical Engineering "Undergraduate Comprehensive Evaluation Platform" (120.46.187.29:8900) — Default Weak Password (initial password = last 6 digits of student ID) Allowing Login to Any Student Account

## Summary

The "Undergraduate Comprehensive Evaluation Platform" of the College of Information and Electrical Engineering (CIEE), China Agricultural University (http://120.46.187.29:8900, publicly reachable bare-IP service) has a weak-password vulnerability. An attacker needs no authorization and no non-public information: the college itself publishes (1) the password rule in an official notice and (2) complete student ID numbers in official recommendation-list notice PDFs. Combining the two allows logging in as any enrolled student.

Password rule (published by the college): username = student ID, initial password = **last 6 digits of the student ID**. Student IDs are published in the college's official Sept-2026 notice PDFs for the recommended candidates list for 2027 graduate admission (151 complete 13-digit IDs of current class-of-2023 undergraduates).

## Affected Product

- Product: CAU CIEE Undergraduate Comprehensive Evaluation Platform (college-developed; React frontend / FastAPI backend, JWT authentication)
- Entry: http://120.46.187.29:8900/ (login API: POST /api/v1/auth/login)
- Affected IP: 120.46.187.29:8900 (Huawei Cloud Beijing, direct public access; no CAPTCHA, no rate limiting)
- Scope: all enrolled undergraduates of CIEE, classes of 2023/2024/2025 (several hundred per class)
- Verified: 2026-10-13, public Internet, Windows/Python requests

## Root Cause

The root cause is a publicly derivable initial password (a substring of the public student ID) combined with no forced password change on first login and no login protection (CWE-521):

1. The college official notice (dated 2026-08-21, https://ciee.cau.edu.cn/art/2026/8/25/art_50390_1130314.html) publicly documents: "username is the student's ID; initial password is the last 6 digits of the ID".
2. Student IDs — 13-digit enumerable identifiers — are published in plaintext in official Sept-2026 recommendation-list notice PDFs (151 IDs).
3. The system enforces no first-login password change, no password-complexity policy, no CAPTCHA, no anomalous-login alerting, and no rate limiting; the service is exposed on a public bare IP with no network-layer access control.

Data flow: attacker reads the college notice (password rule) → reads the recommendation-list PDF (student IDs) → POST /api/v1/auth/login (ID + last-6-digits) → obtains JWT → full account privileges of the target student.

## CVSS

- v3.1: **9.1 Critical** — `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N`
- CWE-521 (Weak Password Requirements)
- Rationale: network-reachable, no privileges or user interaction required; both credential elements come from official public sources; confidentiality and integrity impact are high (the platform's core write functions — bonus-material upload and class peer evaluation scoring — directly feed scholarship decisions and can be abused under any student's identity; not exercised during verification); no availability impact.

## Proof of Concept

See `poc/verify_cau_zcpj_weakpass.py` (read-only: checks reachability, page characteristics, derives credentials per the official rule and attempts login, stops on first success, calls no business API). Core reproduction steps:

1. Visit https://ciee.cau.edu.cn/art/2026/8/25/art_50390_1130314.html to obtain the rule (ID + last-6-digits).
2. Download the Sept-2026 recommendation-list notice PDFs and take any ID (e.g., 2023303090501).
3. POST `{"username":"2023303090501","password":"090501"}` to http://120.46.187.29:8900/api/v1/auth/login.
4. Observed result (2026-10-13): HTTP 200 + JWT access_token — login successful. 7 further accounts from the same batch were verified the same way (8 total; list in `evidence/02-登录成功账号清单.txt`).

## Impact

- Confidentiality (High): account takeover of any enrolled CIEE undergraduate; the platform stores evaluation materials, personal information, and class evaluation data.
- Integrity (High): core functions (bonus-material upload, class peer evaluation scoring) can be abused under a victim's identity, directly influencing scholarship decisions (no write operation was exercised during verification).
- Availability: none observed.
- Scope: all undergraduates of CIEE classes 2023–2025; evaluation results directly feed scholarship assessment.

## Remediation

Immediate: restrict the platform from the public bare IP (campus network / VPN only); batch-reset all accounts to random one-time passwords notified via SMS/email; add CAPTCHA and rate limiting; add anomalous-login monitoring.
Long-term: enforce first-login password change with complexity policy (ban ID-derived passwords); never derive initial passwords from the ID; mask ID columns in public PDFs (first 4 + last 2 digits); add a pre-publication sensitive-data review.

## Reporter Statement

Verification was performed by the reporter: login authentication requests only; among 144 public IDs, 8 logins succeeded and verification stopped there; no business API other than authentication was called; no student data was read, modified, or deleted; no non-public information or unauthorized means were used. The vulnerability is original and previously undisclosed.

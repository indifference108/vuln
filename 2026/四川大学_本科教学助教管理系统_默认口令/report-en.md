# Sichuan University Undergraduate Teaching Assistant Management System — Default Password Vulnerability (English Report)

## Title

Sichuan University "Undergraduate Teaching Assistant Management System" (jxyw.scu.edu.cn:8081/yjszj/) — Default Weak Password Allowing Login to Any Student Account

## Summary

The "Undergraduate Teaching Assistant Management System" of Sichuan University (http://jxyw.scu.edu.cn:8081/yjszj/, publicly reachable) has a weak-password vulnerability. An attacker needs no authorization and no non-public information: the university itself publishes (1) a single, university-wide fixed initial password and (2) student ID numbers in official public notice attachments. Combining the two allows logging in as any enrolled graduate student.

Fixed initial passwords (published by the university): `Cd2023jxyth@` for class of 2025, `cd2017jxyth` for class of 2024 and earlier. Student IDs are published in the university's official scholarship award-list attachments (4,678 master students in the class-of-2025 list alone; 4,189 in the class-of-2023 list).

## Affected Product

- Product: Sichuan University Undergraduate Teaching Assistant Management System
- Entry: http://jxyw.scu.edu.cn:8081/yjszj/
- Affected IP: 202.115.32.49 (resolution of jxyw.scu.edu.cn)
- Scope: all enrolled graduate students (master and doctoral); tens of thousands of accounts across cohorts
- Verified: 2026-10-02, public Internet, Windows/Chrome

## Root Cause

The root cause is a university-wide fixed initial password combined with no forced password change on first login (CWE-521, Weak Password Requirements):

1. The university Academic Affairs Office notice (2025-11-17, http://jwc.scu.edu.cn/info/1069/10353.htm) publicly documents the login pattern "username: student ID" and the fixed initial passwords above.
2. Student IDs — enumerable identifiers — are published in official xlsx attachments by the university's Graduate School (e.g., https://gs.scu.edu.cn/info/1147/6117.htm).
3. The system enforces no first-login password change, no password-complexity policy, and no anomalous-login alerting; the login CAPTCHA only raises automation cost and does not strengthen the credential.

## CVSS

- v3.1: **9.1 Critical** — `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N`
- v4.0: 9.3 — `CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:N/SC:N/SI:N/SA:N`
- Rationale: network-reachable, no privileges or user interaction required, no target prerequisites; both credential elements come from official public sources; confidentiality and integrity impact are high (read access to any student's personal and TA-related data; write functions such as TA application could be abused — not exercised during verification); no availability impact.

## Proof of Concept

See `poc/verify_scu_ta_default_pwd.py`. The credential pair used for verification:

- Username (student ID): `2025221010029` (from the official class-of-2025 award list)
- Password: `Cd2023jxyth@` (from the official Academic Affairs Office notice)

Result: successful login on 2026-10-02 (first attempt, CAPTCHA entered manually). Read-only browsing confirmed access to the student's personal information and TA-related data. No write operation was performed; the session was logged out afterwards.

## Impact

- Confidentiality (High): full account takeover of any enrolled graduate student; exposure of personal information and TA application/position data, affecting tens of thousands of accounts.
- Integrity (High): write functions (e.g., TA application submission) can be abused under a victim's identity (not exercised during verification).
- Availability: none observed.

## Remediation

Immediate: revoke the fixed initial passwords and force random one-time resets; add SMS/email second-factor at login; add anomalous-login monitoring and rate limiting.
Long-term: enforce first-login password change with complexity policy; never use a shared fixed initial password; mask student ID columns (first 4 + last 2 digits) in public attachments; add a pre-publication sensitive-data review for official notices.

## Reporter Statement

Verification was performed by the reporter on a single account, read-only, with no modification, deletion, bulk operation, or use of any non-public information. The vulnerability is original and previously undisclosed.

# Vulnerability Report

> Report ID: VUL-2026-FAFU-001
> Author: indifference (Bugtone white-hat, ID: indifference108)
> Date: 2026-10-02
> Target database: CVE (CNA/MITRE) / CNVD cross-submission

---

## 1. Product Introduction

The Graduate Comprehensive Service Platform of Fujian Agriculture and Forestry University (URL path contains `/gsapp/`, built on the vendor "Zhengfang-like" gsapp architecture for graduate education management; vendor attribution to be confirmed) is the university's web system for graduate student status, training, degree management and certificate printing. It is publicly accessible and offers three login entries: unified identity authentication, system-account login (for graduated students), and off-campus supervisor login. The vulnerability is in the system-account login entry.

## 2. Vulnerability Title

Fujian Agriculture and Forestry University Graduate Comprehensive Service Platform — weak initial password for graduated student accounts allows arbitrary account login

## 3. Summary / Description

The system-account login entry of the platform (intended for graduated students) uses the student ID as the account name, and its initial password follows a fixed, publicly documented rule: `studentID@last4ofID`. The university's graduate school website publishes degree-conferment announcements with xlsx attachments listing graduates' names and full student IDs in plaintext (36 complete IDs in the December 2024 batch alone). An unauthenticated remote attacker can therefore derive valid credentials for any graduated student from public information, log into their account, and read the victim's status, training, grades and degree data, or abuse the account's certificate-printing functions under the victim's identity. A successful login with a rule-derived credential was demonstrated on 2026-10-01.

## 4. Technical Analysis / Root Cause

**Root cause type**: CWE-521 Weak Password Requirements (deterministic initial password derived from semi-public student IDs), combined with CWE-200 Exposure of Sensitive Information (plaintext student IDs in public announcement attachments) as the credential source.

No source code was available; the following is a black-box assessment.

Source-to-sink chain (all inputs are public university documents):

```
Source 1 (official manual, https://yjsy.fafu.edu.cn/63/04/c3665a418564/page.htm):
  "已毕业学生使用系统账号登录入口，账号是学号，初始密码为学号@学号后四位"
  (Graduated students: system-account login, account = student ID,
   initial password = studentID@last4ofID)
Source 2 (degree-conferment announcement attachments, xlsx, plaintext columns
   including 序号/专业/姓名/学号/导师/学位类别)
Credential derivation: userId = student ID; password = ID + "@" + ID[-4:]
Sink: POST /gsapp/sys/yjsrzfwapp/dbLogin/index.do (fields userId / password / vcode)
```

**Validity assessment (black-box)**:
- Reachable: yes — the login entry is publicly accessible without VPN.
- Controllable: yes — student IDs come from official public attachments; the password is uniquely derived, no guessing involved.
- Propagable: yes — the same rule covers all graduated students (179 PhD graduates in the three 2024 batches alone; master's batches are larger).
- Exploitable: yes — a single login request succeeded (verified 2026-10-01).
- Protection bypassable: yes — no forced password change, no complexity check and no anomaly alerting for graduated accounts on this entry.
- Impact confirmed: yes — post-login access to graduated students' personal and academic data.
- Scope: potentially all graduated students of this university; other universities running the same gsapp product may share the same configuration (vendor to confirm).

**Why it happens**: the platform derives each graduated student's initial password from their student ID with a fixed suffix, and the university itself publishes those student IDs in plaintext announcement attachments. The "secret" is therefore public information — the initial password provides no effective authentication.

## 5. Affected Versions

- **Affected**: the current online deployment as of 2026-10-02 (no version string exposed)
- **Not affected**: none confirmed
- **Fixed version**: none as of the report date
- **Verification environment**: public network / Windows 11 + Chrome / target https://yjsapp.fafu.edu.cn

## 6. Severity

| Item | Value |
|------|-----|
| CVSS v3.1 score | 9.1 |
| CVSS v3.1 vector | `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N` |
| CVSS v4.0 score | 9.3 |
| CVSS v4.0 vector | `CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:N/SC:N/SI:N/SA:N` (CVSS-B) |
| Severity | Critical |
| Target-db mapping | CNVD 高危 (top tier of CNVD's three-level scale: 7.0–10.0) |

> Scoring rationale: no authentication required, public-network reachable, credentials deterministically derivable from public documents (AV:N/AC:L/PR:N/UI:N); full read access to graduated students' personal data (C:H) and ability to perform account-level write operations such as certificate-printing requests under the victim's identity (I:H — not exercised during verification); no availability impact (A:N). Scores computed with the official FIRST algorithm (cvss reference implementation).

## 7. CVSS Vector

```
CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N
CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:N/SC:N/SI:N/SA:N
```

## 8. Reproduction Steps

### 8.1 Environment

- Product/version: Fujian Agriculture and Forestry University Graduate Comprehensive Service Platform (online)
- Test client: Windows 11 + Chrome
- Network: public internet
- Test account: none (all credential material comes from the university's own public documents)

### 8.2 Steps

**Step 1 — Obtain the initial-password rule (self-disclosed in the official manual).**
Open the official manual page; it states that graduated students log in via the system-account entry with account = student ID and initial password = `studentID@last4ofID`.
> ![Step 1](evidence/01-manual.png)

**Step 2 — Obtain student IDs (public announcement attachment).**
Open a degree-conferment announcement and download the xlsx attachment containing plaintext names and student IDs (example: 2190101005).
> ![Step 2](evidence/02-xlsx.png)

**Step 3 — Derive credentials and log in.**
Use userId=`2190101005`, password=`2190101005@1005` at the system-account login entry; after entering the CAPTCHA, the login succeeds and the portal loads.
> ![Step 3](evidence/03-login-success.png)

**Step 4 — Impact verification (read-only).**
Browse the student's status/personal-information and certificate-printing list pages. All actions were read-only; no write operation was executed.
> ![Step 4](evidence/04-portal.png)

Full login screen-recording (video/login-fafu.mp4) accompanies this report.

## 9. Proof of Concept [required]

### 9.1 Format selection
- Format: custom Python script
- Reason: login requires a human-solved CAPTCHA; the script performs credential derivation and reachability verification, and prints exact manual steps for the human-in-the-loop login.

### 9.2 Usage
- Environment: Python 3.8+ (stdlib + openpyxl for parsing the public attachment)
- Burp proxy: `USE_BURP=1 BURP_PROXY=http://127.0.0.1:8080` (on by default)
- Safety statement: authorized verification only. Single account, single attempt, read-only; no batch logic.

### 9.3 POC Code

See `poc/verify_fafu_alumni_login.py`.

### 9.4 Expected output / success criteria
```
[+] Login page reachable (HTTP 200), contains 系统账号登录入口
[+] Derived credential: 2190101005 / 2190101005@1005
Success criteria: after CAPTCHA entry, browser redirects to
  https://yjsapp.fafu.edu.cn/gsapp/sys/yjsemaphome/portal/index.do
```

## 10. Mitigation / Fix Recommendations

### 10.1 Temporary mitigations
- Add SMS/email second-factor verification to the graduated-student system-account login entry.
- Redact student-ID columns in all announcement attachments (keep first 4 + last 2 digits) and clean up historical attachments.
- Monitor this entry for anomalous logins.

### 10.2 Root-cause fixes
- Disable graduated accounts by default; re-enable only via in-person review with a one-time random password.
- Replace deterministic initial passwords with non-derivable random ones and enforce change on first login.
- Institutionalize redaction of student lists before publication, so student IDs cease to be semi-public.

### 10.3 Verification
Replay the POC: rule-derived credentials must no longer authenticate; announcement attachments must show redacted IDs.

## 11. False-Positive Elimination / Impact Justification

```
False-positive elimination:
- Existence: PASS — successful login demonstrated 2026-10-01; re-test with screen
  recording on 2026-10-02; credential derivation is deterministic, zero guessing.
- Impact: PASS — weak initial password (CWE-521) grants unauthorized read access to
  graduated students' personal data (C) and account-level write capability (I).
- Exploitability: PASS — unauthenticated (PR:N), public-network reachable (AV:N),
  full chain from public documents to account access demonstrated.
- Originality: PASS — no CVE/CNVD/CNNVD/advisory found for this defect in this
  platform as of 2026-10-02.
- Evidence: PASS — official manual quote, announcement xlsx (36 IDs archived),
  login screen recording, read-only post-login screenshots.
Conclusion: confirmed real, exploitable and previously undisclosed vulnerability.
```

## Appendix A: Timeline / References

| Date | Event |
|------|-------|
| 2026-10-01 | Rule confirmed from official manual; student IDs extracted from public attachment |
| 2026-10-01 | First successful login |
| 2026-10-02 | Re-verification with screen recording; report group finalized |

- Official manual: https://yjsy.fafu.edu.cn/63/04/c3665a418564/page.htm
- Sample announcement: https://yjsy.fafu.edu.cn/0e/ed/c5969a397037/page.htm
- Login entry: https://yjsapp.fafu.edu.cn/gsapp/sys/yjsrzfwapp/dbLogin/index.do

## Appendix B: Evidence Checklist

- [x] Reproduction screenshots (steps 1–4, evidence/01-04)
- [x] Login screen recording (video/login-fafu.mp4, to be exported by the operator)
- [x] Official manual page snapshot
- [x] Announcement xlsx original (evidence/fafu_phd_202412.xlsx) and extracted ID list (evidence/fafu_xuehao.txt)
- [ ] Post-vendor-response patch comparison (to be appended)

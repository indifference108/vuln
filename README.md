# 漏洞披露管理库（CVE / CNVD / CNNVD）

集中管理原创漏洞的审计发现、中英文报告、PoC、证据与三库提交材料。所有 CVE / CNVD / CNNVD 的报送与状态更新都在本仓库进行。

## 目录规范

一个漏洞一个目录，按年份归档：

```
<年份>/<厂商>_<产品>_<漏洞类型>/
├── audit-findings.md     # 代码审计发现（source-to-sink + 八项有效性判定）
├── report-zh.md          # 中文报告（CNVD/CNNVD 口径）
├── report-en.md          # 英文报告（CVE 口径）
├── poc/                  # 可运行 PoC（只读、非武器化、脱敏）
├── evidence/             # 原始报文 / 验证输出 / 源码快照
└── submission/           # cve-submission.md / cnvd-submission.md / cnnvd-submission.md
```

## 漏洞索引

| 目录 | 漏洞 | CWE | CVSS v3.1 | 状态 | CVE | CNVD | CNNVD | 更新时间 |
|------|------|-----|-----------|------|-----|------|-------|----------|
| [2026/zaidmukaddam_Scira_SSRF](2026/zaidmukaddam_Scira_SSRF) | Scira `/api/proxy-image` SSRF | CWE-918 | 7.5 高危 | 已预留 CAN-2026-2038622，待提交 | 待分配 | 待报送 | 待报送 | 2026-09-30 |
| [2024/code-projects_Pharmacy-Management-System_SQLi](2024/code-projects_Pharmacy-Management-System_SQLi) | Pharmacy Management System 1.0 `editManager` SQL 注入（历史归档，经 VulDB 报送） | CWE-89 | 6.3 中危 | 已公开 | CVE-2024-8138 | — | — | 2024-08-25 |

状态流转：`发现验证 → 报告组成稿 → 已报送厂商 → 厂商确认 → 已修复/已分配编号 → 已公开`

## 工作规范

- 报告组按 [cve-cnvd-cnnvd-report](https://github.com/rockmelodies/cve-cnvd-cnnvd-submission-skill) 技能的 9 步流程产出（去误报五道闸门先于成文）。
- PoC 只读、非武器化，真实目标一律脱敏为 `{{TARGET}}` 占位符。
- 证据红线：不使用未授权系统的真实数据；生产环境只做指向自建金丝雀的只读验证。
- 漏洞修复或编号分配前，不在公开渠道披露攻击细节。

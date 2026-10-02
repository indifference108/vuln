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
| [2026/ItzCrazyKns_Vane_SSRF](2026/ItzCrazyKns_Vane_SSRF) | Vane `scrape_url` 工具 SSRF（LLM 工具调用直达 Playwright `page.goto`，可附 `file://` 读本地文件） | CWE-918 | 7.5 高危 | 已报送 MITRE CNA-LR，待审核；已邮件联系维护者 vaneteamproject@gmail.com（2026-09-30），待回复 | CAN-2026-2038643（审核中） | 待报送 | 待报送 | 2026-09-30 |
| [2026/zaidmukaddam_Scira_SSRF](2026/zaidmukaddam_Scira_SSRF) | Scira `/api/proxy-image` SSRF | CWE-918 | 7.5 高危 | 已报送 MITRE CNA-LR，待审核；已邮件联系维护者（2026-09-30），待回复 | CAN-2026-2038622（审核中） | 待报送 | 待报送 | 2026-09-30 |
| [2026/福建农林大学_研究生综合服务平台_毕业生弱口令](2026/福建农林大学_研究生综合服务平台_毕业生弱口令) | 福建农林大学研究生综合服务平台毕业生"系统账号登录入口"弱口令（初始密码规则 + 学位公示明文学号可推导任意毕业生凭据） | CWE-521 | 9.1 严重 | 已报送 CNVD（2026-10-02，事件型，录屏佐证），待受理 | — | 待受理 | 待报送 | 2026-10-02 |
| [2026/四川大学_本科教学助教管理系统_默认口令](2026/四川大学_本科教学助教管理系统_默认口令) | 四川大学本科教学助教管理系统默认弱口令（教务处通知公开全校统一固定口令 + 研究生院公示明文学号，任意研究生账号可登录） | CWE-521 | 9.1 严重 | 已实测登录成功（2026-10-02），CNVD 报送准备中 | — | 待报送 | 待报送 | 2026-10-02 |
| [2024/code-projects_Pharmacy-Management-System_SQLi](2024/code-projects_Pharmacy-Management-System_SQLi) | Pharmacy Management System 1.0 `editManager` SQL 注入（历史归档，经 VulDB 报送） | CWE-89 | 6.3 中危 | 已公开 | CVE-2024-8138 | — | — | 2024-08-25 |
| [2024/Tenda_AC8_缓冲区溢出](2024/Tenda_AC8_缓冲区溢出) | Tenda AC8 `formsetmacfiltercfg` 栈溢出（DoS），V16.03.33.05 | CWE-120 | 中危（CNVD v2 口径） | 已收录 | — | CNVD-2024-38754 | — | 2024-09-20 |
| [2024/Tenda_AC10U_缓冲区溢出](2024/Tenda_AC10U_缓冲区溢出) | Tenda AC10U v1.0 `parse_macfilter_rule` 栈溢出（DoS/可 Ret2libc） | CWE-120 | 高危 | 已收录 | — | CNVD-2024-45023 | — | 2024-10-03 |
| [2025/Tenda_AC20_拒绝服务](2025/Tenda_AC20_拒绝服务) | Tenda AC20 `formSetFirewallCfg` 栈溢出（DoS），V16.03.08.12 | CWE-120 | 中危 | 已收录 | — | CNVD-2026-06063 | — | 2025-10-23 |

状态流转：`发现验证 → 报告组成稿 → 已报送厂商 → 厂商确认 → 已修复/已分配编号 → 已公开`

## 工作规范

- 报告组按 [cve-cnvd-cnnvd-report](https://github.com/rockmelodies/cve-cnvd-cnnvd-submission-skill) 技能的 9 步流程产出（去误报五道闸门先于成文）。
- PoC 只读、非武器化，真实目标一律脱敏为 `{{TARGET}}` 占位符。
- 证据红线：不使用未授权系统的真实数据；生产环境只做指向自建金丝雀的只读验证。
- 漏洞修复或编号分配前，不在公开渠道披露攻击细节。

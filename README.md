# 漏洞披露管理库（CVE / CNVD / CNNVD）

集中管理原创漏洞的审计发现、中英文报告、PoC、证据与三库提交材料。所有 CVE / CNVD / CNNVD 的报送与状态更新都在本仓库进行。

## 目录规范

一个漏洞一个目录，按**漏洞类型**五大类归档（2026-10-09 起由年份制改为类别制，年份信息保留在目录名与索引中）：

```
弱密钥/    # 默认口令、弱口令、初始密码规则可推导凭据（CWE-521）
SQL注入/   # SQL / NoSQL 注入（CWE-89 / CWE-943）
RCE/       # 远程代码执行：SSTI、代码注入、命令注入（CWE-94/78/1336）
SSRF/      # 服务端请求伪造（CWE-918）
逆向/      # 固件逆向类：IoT 缓冲区溢出/拒绝服务（Tenda 系列等）

<类别>/<厂商>_<产品>_<漏洞类型>/
├── audit-findings.md     # 代码审计发现（source-to-sink + 八项有效性判定）
├── report-zh.md          # 中文报告（CNVD/CNNVD 口径）
├── report-en.md          # 英文报告（CVE 口径）
├── poc/                  # 可运行 PoC（只读、非武器化、脱敏）
├── evidence/             # 原始报文 / 验证输出 / 源码快照
└── submission/           # cve-submission.md / cnvd-submission.md / cnnvd-submission.md
```

## 漏洞索引

### 弱密钥

| 目录 | 漏洞 | CWE | CVSS v3.1 | 状态 | CVE | CNVD | 更新时间 |
|------|------|-----|-----------|------|-----|------|----------|
| [四川大学_本科教学助教管理系统_默认口令](弱密钥/四川大学_本科教学助教管理系统_默认口令) | 四川大学本科教学助教管理系统默认弱口令（教务处通知公开全校统一固定口令 + 研究生院公示明文学号，任意研究生账号可登录） | CWE-521 | 9.1 严重 | 已实测登录成功，已报送 CNVD | — | CNVD-C-2026-613323（未归档） | 2026-10-02 |
| [福建农林大学_研究生综合服务平台_毕业生弱口令](弱密钥/福建农林大学_研究生综合服务平台_毕业生弱口令) | 福建农林大学研究生综合服务平台毕业生"系统账号登录入口"弱口令（初始密码规则 + 学位公示明文学号可推导任意毕业生凭据） | CWE-521 | 9.1 严重 | 已报送 CNVD（事件型，录屏佐证），已受理 | — | CNVD-C-2026-613312（未归档） | 2026-10-02 |

### SQL 注入

| 目录 | 漏洞 | CWE | CVSS v3.1 | 状态 | CVE | CNVD | 更新时间 |
|------|------|-----|-----------|------|-----|------|----------|
| [labring_FastGPT_NoSQLi_CVE-2026-79483](SQL注入/labring_FastGPT_NoSQLi_CVE-2026-79483) | FastGPT 社区版 4.10.0–4.14.0 `getHistories` NoSQL 注入未授权读取全平台用户聊天历史标题 | CWE-943 | 5.3 中危 | 已报送 CNVD 事件型×2（2026-10-08：广州工商学院、武汉自规局），待受理 | CVE-2026-79483 | 已报送（2026-10-08） | 2026-10-08 |
| [武汉自规局SQL注入](SQL注入/武汉自规局SQL注入) | 79483 事件型（武汉自规局）：报送 docx / 附件包 / 录屏源 + CNVD 补充危害材料（4 图） | CWE-943 | 5.3 中危 | 已提交；10-08 被要求补危害截图，补充材料已传 | CVE-2026-79483 | 已报送 | 2026-10-08 |
| [广东工商学院SQL注入](SQL注入/广东工商学院SQL注入) | 79483 事件型（广州工商学院）：录屏源 | CWE-943 | 5.3 中危 | 已报送 | CVE-2026-79483 | 已报送（2026-10-08） | 2026-10-08 |
| [武汉自规局_FastGPT登录NoSQLi_CVE-2026-40351](SQL注入/武汉自规局_FastGPT登录NoSQLi_CVE-2026-40351) | FastGPT <4.14.9.5 登录接口 NoSQL 注入（root/Owner 实测，9.8 分） | CWE-943 | 9.8 严重 | ★定案待提交（证据+POC 齐，差录屏） | CVE-2026-40351 | 待报送 | 2026-10-08 |
| [智学客教育云_FastGPT登录NoSQLi_CVE-2026-40351](SQL注入/智学客教育云_FastGPT登录NoSQLi_CVE-2026-40351) | 同上：智学客教育云 19 所高校入口同一后端 | CWE-943 | 9.8 严重 | ★定案待提交（证据+POC+入口清单齐，差录屏） | CVE-2026-40351 | 待报送 | 2026-10-08 |
| [FastGPT_40351_全国批量扫描_20261008](SQL注入/FastGPT_40351_全国批量扫描_20261008) | 40351 全国独立实例批量扫描：**254 命中（root/Owner）**，含政府/企业高价值目标短名单 | CWE-943 | 9.8 严重 | 扫描定案完成，待挑目标报送（安陆市政府/帆软/南孚优先） | CVE-2026-40351 | 待报送 | 2026-10-08 |
| [code-projects_Pharmacy-Management-System_SQLi](SQL注入/code-projects_Pharmacy-Management-System_SQLi) | Pharmacy Management System 1.0 `editManager` SQL 注入（历史归档，经 VulDB 报送） | CWE-89 | 6.3 中危 | 已公开 | CVE-2024-8138 | — | 2024-08-25 |

### RCE

| 目录 | 漏洞 | CWE | CVSS v3.1 | 状态 | CVE | CNVD | 更新时间 |
|------|------|-----|-----------|------|-----|------|----------|
| [infiniflow_RAGFlow_SSTI_CVE-2026-28797](RCE/infiniflow_RAGFlow_SSTI_CVE-2026-28797) | RAGFlow ≤v0.24.0 Agent 组件 SSTI→RCE（12 个公网实例 root 实测） | CWE-94/1336 | 9.8 严重 | 已报送 CNVD 事件型×3（2026-10-08），官方修复 v0.25.0 | CVE-2026-28797 | 已报送×3（2026-10-08） | 2026-10-08 |
| [深圳市博商管理科学研究院_RAGFlow_SSTI_RCE](RCE/深圳市博商管理科学研究院_RAGFlow_SSTI_RCE) | 28797 事件型：报送 docx + 附件 zip + 录屏 | CWE-94 | 9.8 严重 | 已提交（10-08） | CVE-2026-28797 | 已报送 | 2026-10-08 |
| [上海章节零一_RAGFlow_SSTI_RCE](RCE/上海章节零一_RAGFlow_SSTI_RCE) | 28797 事件型：报送 docx + 附件 zip + 录屏 | CWE-94 | 9.8 严重 | 已提交（10-08） | CVE-2026-28797 | 已报送 | 2026-10-08 |
| [陈玮伦企管咨询_RAGFlow_SSTI_RCE](RCE/陈玮伦企管咨询_RAGFlow_SSTI_RCE) | 28797 事件型：报送 docx + 附件 zip + 录屏 | CWE-94 | 9.8 严重 | 已提交（10-08） | CVE-2026-28797 | 已报送 | 2026-10-08 |
| [Langflow_CVE-2026-9198_批量扫描定案](RCE/Langflow_CVE-2026-9198_批量扫描定案) | Langflow 1.0.0–1.10.0 auto_login+validate/code 未授权 RCE 批量定案（8 国外实例；CN 范围内实例全关；1 蜜罐剔除） | CWE-94 | 9.8 严重 | 扫描定案完成；CVE 已公开+KEV，无 CN 受害实例可报送 | CVE-2026-9198 | — | 2026-10-08 |

### SSRF

| 目录 | 漏洞 | CWE | CVSS v3.1 | 状态 | CVE | CNVD | 更新时间 |
|------|------|-----|-----------|------|-----|------|----------|
| [ItzCrazyKns_Vane_SSRF](SSRF/ItzCrazyKns_Vane_SSRF) | Vane `scrape_url` 工具 SSRF（LLM 工具调用直达 Playwright `page.goto`，可附 `file://` 读本地文件） | CWE-918 | 7.5 高危 | 已报送 MITRE CNA-LR，待审核 | CAN-2026-2038643（审核中） | 待报送 | 2026-09-30 |
| [zaidmukaddam_Scira_SSRF](SSRF/zaidmukaddam_Scira_SSRF) | Scira `/api/proxy-image` SSRF | CWE-918 | 7.5 高危 | 已报送 MITRE CNA-LR，待审核 | CAN-2026-2038622（审核中） | 待报送 | 2026-09-30 |

### 逆向（固件/IoT）

| 目录 | 漏洞 | CWE | CVSS v3.1 | 状态 | CVE | CNVD | 更新时间 |
|------|------|-----|-----------|------|-----|------|----------|
| [Tenda_AC8_缓冲区溢出](逆向/Tenda_AC8_缓冲区溢出) | Tenda AC8 `formsetmacfiltercfg` 栈溢出（DoS），V16.03.33.05 | CWE-120 | 中危（CNVD v2 口径） | 已收录 | — | CNVD-2024-38754 | 2024-09-20 |
| [Tenda_AC10U_缓冲区溢出](逆向/Tenda_AC10U_缓冲区溢出) | Tenda AC10U v1.0 `parse_macfilter_rule` 栈溢出（DoS/可 Ret2libc） | CWE-120 | 高危 | 已收录 | — | CNVD-2024-45023 | 2024-10-03 |
| [Tenda_AC20_拒绝服务](逆向/Tenda_AC20_拒绝服务) | Tenda AC20 `formSetFirewallCfg` 栈溢出（DoS），V16.03.08.12 | CWE-120 | 中危 | 已收录 | — | CNVD-2026-06063 | 2025-10-23 |

状态流转：`发现验证 → 报告组成稿 → 已报送厂商 → 厂商确认 → 已修复/已分配编号 → 已公开`

## 工作规范

- 报告组按 [cve-cnvd-cnnvd-report](https://github.com/rockmelodies/cve-cnvd-cnnvd-submission-skill) 技能的 9 步流程产出（去误报五道闸门先于成文）。
- PoC 只读、非武器化，真实目标一律脱敏为 `{{TARGET}}` 占位符。
- 证据红线：不使用未授权系统的真实数据；生产环境只做指向自建金丝雀的只读验证。
- 漏洞修复或编号分配前，不在公开渠道披露攻击细节。

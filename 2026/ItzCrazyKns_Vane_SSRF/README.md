# Vane scrape_url SSRF — 复现与报告组

ItzCrazyKns/Vane 1.12.2 及更早版本 `scrape_url` 工具存在服务器端请求伪造（SSRF）漏洞：
`POST /api/search`（无认证）→ Researcher 工具循环 → `scrape_url`（LLM 控制 URL）→
`Scraper.scrape()` → Playwright `page.goto(url)`，全程无协议/主机/IP 校验。
可读取内网 HTTP 服务与云元数据端点，`file://` 协议还可读取服务器本地文件。

- CWE-918 ｜ CVSS 3.1: 7.5 (High) ｜ CVSS 4.0: 8.7 (High)
- 漏洞细节已于 2026-05-25 由 [issue #1140](https://github.com/ItzCrazyKns/Vane/issues/1140) 公开，尚无 CVE 编号；
  本仓库为独立复现与验证，可作为 CVE 申报支持材料。

## 目录

| 文件 | 说明 |
|------|------|
| `report-zh.md` / `report-en.md` | 中文 / 英文漏洞报告（CVE/CNVD/CNNVD 口径） |
| `audit-findings.md` | 代码审计发现（source-to-sink 调用链 + 固定字段） |
| `poc/verify_vane_ssrf.py` | 主验证脚本（live / lab 双模式，内置 Burp 代理开关） |
| `poc/README.md` | POC 使用说明 |
| `evidence/` | 复现截图、请求/响应原文、canary 与 mock LLM 日志 |

## 快速验证（离线完整复现）

```bash
git clone https://github.com/ItzCrazyKns/Vane.git && cd Vane
npm i --legacy-peer-deps && npx playwright install chromium-headless-shell
# 另开终端：python verify_vane_ssrf.py lab   （按提示把 data/config.json 指向 mock LLM）
```

> 仅供授权测试与漏洞验证。

# 审计发现（audit-findings）

> 漏洞：zaidmukaddam Scira `/api/proxy-image` SSRF（CWE-918）
> 审计日期：2026-09-29 ｜ 审计对象：仓库 main 分支 commit `e1692f5bdec7ec3f6482a24e0c6cf9b483d810f9`（2026-08-13）

```
标题: zaidmukaddam Scira /api/proxy-image 服务端请求伪造漏洞
严重等级: 高危（CVSS v3.1 7.5 / v4.0 7.7）
受影响入口: GET /api/proxy-image（Next.js App Router 路由，公网可达）
鉴权要求: 无（路由未挂载任何鉴权中间件，未授权即可调用）
用户可控输入: 查询参数 url（request.nextUrl.searchParams.get('url')），完全可控，无长度/字符限制

Source-to-sink 调用链:
  用户输入 url 参数
    → app/api/proxy-image/route.ts:5  GET() 读取 searchParams.get('url')
    → route.ts:12-16  仅做 new URL(url) 语法校验（无协议/地址/域名检查）
    → route.ts:19  fetch(url, ...)  ← Sink：服务端对攻击者可控 URL 发起请求
    → route.ts:30-38  响应体与 Content-Type 原样回传攻击者（全读取 SSRF）

Sink: fetch(url, { headers: { 'User-Agent': 'Mozilla/5.0 ...' } })
      位置：app/api/proxy-image/route.ts 第 19 行

同源/相似受影响路由: 全仓检索未发现第二个「用户可控 URL 直接进 fetch」的未授权路由；
      该文件是唯一 proxy 路由（app/api/proxy-image/route.ts，45 行）。

防护判断:
  - 唯一校验是 new URL() 语法解析（route.ts:12-16），不构成安全控制；
  - 无协议白名单（http/https 之外由运行时兜底，file:// 被 undici 拒绝而非应用层拦截，实测 T7 返回 500）；
  - 无 DNS 解析后 IP 校验，回环/私网/链路本地/保留地址全部可达（实测 T3 读回 127.0.0.1 内容）；
  - fetch 默认跟随重定向，302 可跳入 127.0.0.1（实测 T8），任何「只检查初始 URL」的修补均可被绕过；
  - 无 Content-Type 限制（实测 T2 透传 text/plain；scira.ai 实测透传 text/html）；
  - 无响应大小与超时限制；
  - 响应带 Cache-Control: public, max-age=31536000, immutable + ACAO:*，
    scira.ai 生产环境实测 X-Vercel-Cache: HIT，攻击者投放内容可被边缘缓存一年。

安全 Payload（非破坏性，只读）:
  http://127.0.0.1:8899/  （自建 canary，返回随机令牌，仅证明回环可读）

Burp 原始请求包:
  GET /api/proxy-image?url=http%3A%2F%2F127.0.0.1%3A8899%2F HTTP/1.1
  Host: {{TARGET}}
  User-Agent: curl/8.13.0
  Accept: */*
  （期望响应：HTTP 200，body 为 canary 令牌）

影响（单点）:
  未授权攻击者以服务器身份访问任意 URL 并读取响应：回环服务、内网 HTTP 服务、
  云实例元数据（169.254.169.254，云上部署可窃取临时 IAM 凭证）；
  借 Vercel 边缘缓存将任意内容以 scira.ai 域名长期投递（钓鱼/缓存投毒）；
  响应状态/耗时差异可用于内网端口探测（实测 T4 Redis 端口返回 500，与开放 HTTP 端口可区分）。

攻击链 / 综合影响:
  SSRF + 内网扫描：以本漏洞为支点探测并读取内网服务，绘制内网拓扑；
  SSRF + 云元数据：窃取 IAM 临时凭证后横向控制云资源（综合风险可达 Critical，取决于部署环境）；
  SSRF + 边缘缓存投毒：以受信域名分发钓鱼内容，放大社会工程攻击面。

证据文件和行号:
  - app/api/proxy-image/route.ts:5（source）、:12-16（唯一校验）、:19（sink）、:30-38（回显）
  - 证据快照：证据/route.ts（45 行全文）
  - 实测报文：证据/exp-results/T1~T8（headers+body）
  - 生产实测：证据/scira-ai-webhook-poc.txt（2026-09-28，scira.ai）

限制说明:
  - T5（169.254.169.254）在 WSL 测试环境返回 500，因本机无云元数据服务；云上部署将真实命中。
  - T4（Redis）返回 500，因 Redis 响应非合法 HTTP 报文，undici 解析失败；连接已建立，端口探测仍成立。
  - file:// 协议被 Node undici 拦截，非应用层防护，不构成缓解。
  - 未在 scira.ai 做任何内网目标测试，生产验证仅限指向自建 webhook.site 金丝雀的只读请求。
```

## 有效性判定（code-audit §8 八项）

| # | 判定 | 依据 |
|---|------|------|
| 可达 | ✅ | GET /api/proxy-image 公网路由，生产站 scira.ai 实测可达（X-Matched-Path: /api/proxy-image） |
| 可控 | ✅ | url 参数完全可控，仅语法校验 |
| 可传播 | ✅ | source→sink 间无鉴权、无白名单、无地址校验，零打断 |
| 可利用 | ✅ | fetch 执行并把响应回传攻击者，实测读回 127.0.0.1 canary 令牌 |
| 防护可绕过 | ✅ | 无有效防护；即便补初始 URL 检查，302 重定向仍可绕过（实测 T8） |
| 可复现 | ✅ | 8 项矩阵在干净默认部署稳定复现，Burp 原始请求包见上 |
| 影响成立 | ✅ | 机密性受损：回环/内网/元数据内容可读 |
| 影响范围 | ✅ | 可组合内网扫描、云凭证窃取、边缘缓存投毒，见「攻击链」 |

## 扫描线索（scripts 实测，仅线索非结论）

- `pattern_scanner.py` 扫 scira 全仓：SSRF 规则 0 命中（规则面向 Java/PHP 模式，未覆盖 TS fetch 场景）→ 自动扫描漏报，人工代码审计定位。
- `secret_finder.py`：0 命中（占位 .env 未入库，符合预期）。
- `report_generator.py`：汇总正常（已修复其 HTML 模板 `.format()` 与 CSS 花括号冲突的 KeyError）。

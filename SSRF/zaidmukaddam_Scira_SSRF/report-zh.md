# 漏洞报告（中文）

> 报告编号：VUL-2026-SCIRA-SSRF-001
> 撰写人 / 单位：{{待填：署名}}
> 报告日期：2026-09-30
> 目标库：CVE（GitHub Security Advisory）/ CNVD / CNNVD / 厂商通报

---

## 1. 产品介绍（Product Introduction）

Scira 是 zaidmukaddam 开发的开源 AI 搜索引擎（GitHub 约 11.9k Star，前身为 MiniPerplx），基于 Next.js 构建，用于联网检索并给出带引用的答案。项目以自部署和官方站点 scira.ai 两种形态提供服务。本次漏洞位于其图片代理接口 `/api/proxy-image`。

## 2. 漏洞标题（Vulnerability Title）

zaidmukaddam Scira（截至 commit e1692f5）存在服务端请求伪造漏洞

## 3. 漏洞描述（Description）

Scira（截至 2026-08-13 的 main 分支最新提交 e1692f5）的图片代理接口 `/api/proxy-image` 存在服务端请求伪造（SSRF）漏洞。攻击者无需认证，通过 `url` 参数传入任意地址，即可让服务器向内网、回环、云元数据等地址发起请求，并把响应内容读回，导致机密性受影响；官方站点 scira.ai 同样受影响，响应经 Vercel 边缘节点长期缓存，攻击者可借此以 scira.ai 域名投递任意内容。

## 4. 漏洞分析（Analysis / 根因定位）

**根因类型**：CWE-918 服务端请求伪造（Server-Side Request Forgery）

**Source-to-sink 调用链**：
```
用户输入（url 参数，位于 app/api/proxy-image/route.ts GET()，第 5 行）
  → 第 12-16 行仅做 new URL(url) 语法校验，无协议/地址/域名检查
  → fetch(url)（危险函数/Sink，route.ts 第 19 行）
  → 响应体与 Content-Type 原样回传（route.ts 第 30-38 行）
```

**代码定位**：
```text
文件：app/api/proxy-image/route.ts（commit e1692f5）
行号：5（source）、12-16（唯一校验）、19（sink）、30-38（回显）
关键代码：
  const url = request.nextUrl.searchParams.get('url');
  try { new URL(url); } catch { return NextResponse.json({ error: 'Invalid URL' }, { status: 400 }); }
  const response = await fetch(url, { headers: { 'User-Agent': 'Mozilla/5.0 ...' } });
  const contentType = response.headers.get('content-type') || 'image/jpeg';
  return new NextResponse(response.body, { headers: {
    'Content-Type': contentType,
    'Cache-Control': 'public, max-age=31536000, immutable',
    'Access-Control-Allow-Origin': '*',
  }});
```

**有效性判定**（按 code-audit §8）：
- 可达：`/api/proxy-image` 为公网路由，scira.ai 实测可达（响应头 `X-Matched-Path: /api/proxy-image`）。
- 可控：`url` 参数完全由攻击者控制，仅做语法校验。
- 可传播：source 到 sink 之间无鉴权、无白名单、无地址校验。
- 可利用：实测服务器代读 127.0.0.1 上的 canary 令牌并回传。
- 防护可绕过：当前无有效防护；即便补上「初始 URL 检查」，fetch 默认跟随 302，实测可经重定向跳入回环。
- 可复现：8 项测试矩阵在干净默认部署稳定复现；Burp 原始请求包见 audit-findings.md。
- 影响成立：回环/内网/云元数据内容可被读取，机密性受损。
- 影响范围：可组合内网扫描、云凭证窃取、边缘缓存投毒扩大影响。

**成因分析**：该接口把用户传入的 `url` 直接交给服务端 `fetch` 发起请求，只校验 URL 语法是否合法，没有限制协议、目标地址和响应内容类型。服务器因此会以自身网络位置访问攻击者指定的任意地址，并把读到的内容还给攻击者。

## 5. 影响版本（Affected Versions）

- **受影响版本**：截至 commit e1692f5（2026-08-13）的全部版本；项目无 Release/Tag，漏洞代码自引入起持续存在
- **不受影响版本**：暂无确认的不受影响版本
- **修复版本**：截至报告日期暂无修复版本
- **验证环境**：commit e1692f5 / WSL2 Ubuntu 26.04 / Node.js 22.20 / Next.js dev（pnpm dev）；生产验证：scira.ai（Vercel）

## 6. 漏洞等级（Severity）

| 项目 | 值 |
|------|-----|
| CVSS v3.1 分数 | 7.5 |
| CVSS v3.1 向量 | `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N` |
| CVSS v4.0 分数 | 7.7 |
| CVSS v4.0 向量 | `CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:N/VI:N/VA:N/SC:H/SI:N/SA:N` |
| 危害等级 | 高危 |
| 对应目标库等级 | CNVD 高危 / CNNVD 高危 |

> 评分依据：无需认证（PR:N）、公网可达（AV:N）、单请求即可触发（AC:L、UI:N）；服务器代读内网与云元数据内容，机密性影响高（v3.1 C:H；v4.0 影响落在后续系统 SC:H）。分数用 first.org 算法库复算，向量与分数自洽。
> 备注：若评审认为 SSRF 使影响越出组件安全边界，v3.1 可按 `S:C` 调整为 8.6，仍为高危。

## 7. CVSS 向量（CVSS Vector）

```
CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N
CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:N/VI:N/VA:N/SC:H/SI:N/SA:N
```

## 8. 漏洞复现过程（Reproduction Steps）

### 8.1 复现环境

- 产品/版本：Scira commit e1692f5
- 系统/运行时：WSL2 Ubuntu 26.04 + Node.js 22.20（PostgreSQL 16、Redis 7 容器）
- 网络位置：本地（自部署）；另在公网官方站点 scira.ai 做了只读验证
- 测试账号：无

### 8.2 复现步骤

**步骤 1 — 确认代理基线**
请求 `/api/proxy-image?url=https://httpbin.org/image/png`，返回 200 和 PNG 图片，说明接口会代取任意 URL。
> 证据：evidence/01-wsl-repro-captures-20260929.txt（T1）

**步骤 2 — 发送恶意请求**
在本机 127.0.0.1:8899 起一个只读 canary 服务（返回随机令牌），构造请求：
```http
GET /api/proxy-image?url=http%3A%2F%2F127.0.0.1%3A8899%2F HTTP/1.1
Host: {{TARGET}}
```

**步骤 3 — 触发回显**
响应 200，响应体为 canary 令牌，证明服务器代读了回环地址的内容：
```
HTTP/1.1 200 OK
Content-Type: text/plain

SCIRA_SSRF_CANARY_1790697885
```
> 证据：evidence/01-wsl-repro-captures-20260929.txt（T3）

**步骤 4 — 影响验证**
两项补充验证：其一，经 302 重定向（`url=http://127.0.0.1:8900/hop`，跳转至 canary）同样读回令牌，说明 fetch 跟随重定向，任何只检查初始 URL 的修补都能被绕过；其二，对官方站点 scira.ai 请求自建 webhook.site 金丝雀地址，返回 200 且响应体为金丝雀内容，响应头 `X-Vercel-Cache: HIT`、`Cache-Control: public, max-age=31536000, immutable`、`Content-Type: text/html`，证明生产环境同样存在该漏洞，且攻击者投放的内容会被边缘节点以 scira.ai 域名缓存一年。
> 证据：evidence/01-wsl-repro-captures-20260929.txt（T8）、evidence/04-scira-ai-production-20260928.txt

## 9. 漏洞复现 POC（Proof of Concept）

### 9.1 格式选择
- 选用格式：nuclei 模板 + 自定义 Python 脚本（两份均放入 poc/）
- 选择理由：漏洞为单请求、无状态，nuclei 最轻；自定义脚本额外覆盖「回环 canary + 302 重定向」两个 nuclei 不便表达的场景，且默认支持代理到 Burp 逐包分析

### 9.2 运行说明
- 运行环境：Python 3（依赖 requests）/ nuclei
- **代理到 Burp**：自定义脚本 `USE_BURP=1 BURP_PROXY=http://127.0.0.1:8080 python3 poc.py`；nuclei 用 `-proxy http://127.0.0.1:8080`
- 安全声明：本 POC 仅用于授权测试与漏洞验证，全部为只读请求，禁止用于未授权系统。

### 9.3 POC 代码

nuclei（`poc/scira-proxy-image-ssrf-nuclei.yaml`，payload 指向 httpbin 公开回显端点，不触碰内网）：
```bash
nuclei -t poc/scira-proxy-image-ssrf-nuclei.yaml -u http://{{TARGET}}/
```

自定义脚本（`poc/poc.py`，目标用环境变量注入，canary 令牌每次随机生成）：
```bash
TARGET=http://{{TARGET}} USE_BURP=1 python3 poc/poc.py
```

### 9.4 预期输出 / 成功判定
```
== 1. 基线：外网公开回显端点 ==        [+] 基线通过：代理工作正常
== 2. 回环 SSRF：代读 127.0.0.1 canary 令牌 ==  [+] 命中：服务器代读了回环内容
== 3. 重定向：302 跳入回环 ==          [+] 命中：fetch 跟随 302 进入回环
[*] 结果：3/3 项通过，SSRF 确认（退出码 0）
```
> 实测输出：evidence/05-poc-py-run-output-20260930.txt

## 10. 修复建议（Fix Recommendations）

### 10.1 临时缓解措施
- 在网络层限制服务器出站：禁止 Web 服务器访问回环、私网、169.254.0.0/16 地址段。
- 若图片代理非核心功能，临时下线 `/api/proxy-image`。
- 移除该路由响应的 `Cache-Control: immutable` 长缓存，避免已投放内容继续命中边缘缓存。

### 10.2 根治修复方案
- 仅允许 `http`/`https` 协议；对主机名做 DNS 解析，拒绝解析到回环、私网、链路本地、保留地址段的目标，并对每一次重定向跳转重复该校验（或直接禁用重定向跟随）。
- 业务上可行的前提下改为图片源域名白名单。
- 校验响应 `Content-Type` 必须为 `image/*`（按 magic bytes 复核更稳妥），限制响应大小（如 5 MB）与超时时间。
- 收敛 `Access-Control-Allow-Origin: *`。

### 10.3 修复验证
重放 poc/poc.py 与 nuclei 模板：基线请求应仍正常（代理合法图片源），回环与重定向两项应返回 4xx/拒绝，三项不再同时通过。

## 11. 去误报说明（False-Positive Elimination）

```
去误报核验结论：
- 存在性：✅ 已在 clean 默认安装环境稳定复现（8 项矩阵 + poc.py 3/3 通过，复现 ≥3 次）；scira.ai 生产站只读验证同样成立
- 定性：✅ 构成服务端请求伪造（CWE-918），机密性受影响
- 可利用性：✅ 无需认证（PR:N），公网可达（AV:N），单请求触发，影响确定
- 原创性：✅ 检索 NVD/cve.org、GitHub Advisories（仓库无已发布安全公告）、仓库 issue（"ssrf" 0 命中）、公开 writeup，均无同洞记录；根因位于项目自有代码，非第三方依赖已知 CVE
- 证据：✅ 完整请求/响应原文（T1-T8）、生产站 curl 会话、源码定位（route.ts 行号）、poc.py 实测输出
- 代码级判定（有源码）：✅ 可达/可控/可传播/可利用/防护可绕过/可复现/影响成立/影响范围，八项全过
结论：确认为真实、可利用、未公开漏洞，可提交。
```

---

## 附录 A：参考链接 / 时间线

| 时间 | 事项 |
|------|------|
| 2026-09-28 | 首次发现并验证（自部署 + scira.ai 只读验证） |
| 2026-09-29 | WSL 干净环境 8 项矩阵复现，完成根因定位 |
| 2026-09-30 | poc.py / nuclei 模板实测通过，报告成稿 |
| （待填） | 通过 GitHub Security Advisory 报告维护者 |

- 漏洞源码：https://github.com/zaidmukaddam/scira/blob/main/app/api/proxy-image/route.ts
- 项目主页：https://scira.ai
- 相关 CVE/CNVD/CNNVD：暂无（待分配）

## 附录 B：证据清单

- [x] HTTP 请求/响应原文（evidence/01、02，T1-T8 原始报文）
- [x] 生产站验证会话（evidence/04）
- [x] 代码级定位证据（evidence/03-vulnerable-route.ts）
- [x] POC 实测输出（evidence/05）
- [ ] 复现截图（以原始报文与脚本输出替代；如需截图可按 §8 步骤补拍）
- [ ] 版本差异/补丁比对（暂无官方补丁）

